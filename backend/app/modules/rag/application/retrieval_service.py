"""RAG retrieval and answer services — API routes delegate here."""
from __future__ import annotations

import asyncio
import logging
import time
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.modules.rag.application.answer_cache import (
    get_cached_rag_answer,
    set_cached_rag_answer,
)
from backend.app.modules.rag.application.citation_service import CitationService
from backend.app.modules.rag.application.retrieve_cache import (
    get_cached_retrieve,
    retrieval_policy_revision,
    set_cached_retrieve,
)
from backend.app.modules.rag.application.hybrid_retrieval import reciprocal_rank_fusion
from backend.app.modules.rag.application.rerank_service import filter_by_score_threshold, rerank_chunks
from backend.app.modules.rag.application.embedding_service import EmbeddingService
from backend.app.modules.rag.application.rag_context_builder import RagContextBuilder
from backend.app.modules.rag.application.rag_policy_service import RagPolicyService, get_rag_policy_service
from backend.app.modules.rag.domain.models import RagAnswer, RetrievedChunk
from backend.app.modules.rag.domain.value_objects import AccessContext, RetrievalFilters
from backend.app.modules.rag.infrastructure.pgvector_adapter import get_vector_store
from backend.app.modules.rag.infrastructure.repositories import get_rag_repository

logger = logging.getLogger(__name__)


class RetrievalService:
    def __init__(
        self,
        *,
        embedding_service: EmbeddingService | None = None,
        policy_service: RagPolicyService | None = None,
    ) -> None:
        self._embeddings = embedding_service or EmbeddingService()
        self._policy = policy_service or get_rag_policy_service()

    async def retrieve(
        self,
        db: AsyncSession,
        query: str,
        *,
        access: AccessContext,
        top_k: int | None = None,
        filters: RetrievalFilters | None = None,
    ) -> list[RetrievedChunk]:
        if not settings.RAG_ENABLED:
            return []

        started = time.perf_counter()
        top_k = top_k or settings.RAG_TOP_K
        filters = filters or RetrievalFilters()
        normalized_query = query.strip()

        allowed_owner_ids = await self._policy.allowed_owner_ids_for_retrieval(
            db,
            access=access,
            project_id=access.project_id,
        )
        policy_revision = retrieval_policy_revision(
            is_admin=access.is_admin,
            allowed_owner_ids=allowed_owner_ids,
            source_types=filters.source_types,
        )

        cached = await get_cached_retrieve(
            user_id=access.user_id,
            project_id=access.project_id,
            query=normalized_query,
            top_k=top_k,
            document_ids=filters.document_ids,
            policy_revision=policy_revision,
        )
        if cached is not None:
            logger.debug(
                "rag_retrieve_cache_hit",
                extra={
                    "user_id": access.user_id,
                    "project_id": access.project_id,
                    "hits": len(cached),
                },
            )
            return cached

        query_embedding = await self._embeddings.embed_query(normalized_query)
        store = get_vector_store(db)
        fetch_k = max(top_k, min(top_k * 4, 20))
        vector_chunks, lexical_chunks = await asyncio.gather(
            store.similarity_search(
                query_embedding,
                user_id=access.user_id,
                project_id=access.project_id,
                top_k=fetch_k,
                allowed_user_ids=allowed_owner_ids,
                document_ids=filters.document_ids,
                source_types=filters.source_types,
            ),
            store.lexical_search(
                normalized_query,
                user_id=access.user_id,
                project_id=access.project_id,
                top_k=fetch_k,
                allowed_user_ids=allowed_owner_ids,
                document_ids=filters.document_ids,
                source_types=filters.source_types,
            ),
        )
        chunks = reciprocal_rank_fusion(vector_chunks, lexical_chunks, top_k=fetch_k)
        chunks = rerank_chunks(normalized_query, chunks, top_k)
        chunks = filter_by_score_threshold(chunks)
        await set_cached_retrieve(
            user_id=access.user_id,
            project_id=access.project_id,
            query=normalized_query,
            top_k=top_k,
            document_ids=filters.document_ids,
            policy_revision=policy_revision,
            chunks=chunks,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        extra = {
            "user_id": access.user_id,
            "project_id": access.project_id,
            "hits": len(chunks),
            "latency_ms": latency_ms,
        }
        if latency_ms >= settings.SLOW_EXTERNAL_CALL_MS:
            logger.warning("rag_retrieve_slow", extra=extra)
        else:
            logger.info("rag_retrieve_complete", extra=extra)
        return chunks


class RagAnswerService:
    def __init__(
        self,
        *,
        retrieval_service: RetrievalService | None = None,
        context_builder: RagContextBuilder | None = None,
        citation_service: CitationService | None = None,
    ) -> None:
        self._retrieval = retrieval_service or RetrievalService()
        self._context = context_builder or RagContextBuilder()
        self._citations = citation_service or CitationService()
        self._repo = get_rag_repository()

    async def answer(
        self,
        db: AsyncSession,
        query: str,
        *,
        access: AccessContext,
        top_k: int | None = None,
    ) -> RagAnswer:
        started = time.perf_counter()

        if not settings.RAG_ENABLED:
            return RagAnswer(
                query=query,
                answer="Document RAG is disabled on this server.",
                no_context=True,
            )

        async def _load_memory_context() -> str:
            if not access.user_id:
                return ""
            try:
                from backend.app.modules.memory.service import get_memory_service

                return await get_memory_service().read_l3_concat(
                    db, user_id=uuid.UUID(access.user_id)
                )
            except Exception:
                logger.warning("rag_memory_load_failed user_id=%s", access.user_id)
                return ""

        chunks, memory_context = await asyncio.gather(
            self._retrieval.retrieve(
                db,
                query,
                access=access,
                top_k=top_k,
            ),
            _load_memory_context(),
        )

        resolved_top_k = top_k or settings.RAG_TOP_K
        allowed_owner_ids = await self._retrieval._policy.allowed_owner_ids_for_retrieval(
            db,
            access=access,
            project_id=access.project_id,
        )
        policy_revision = retrieval_policy_revision(
            is_admin=access.is_admin,
            allowed_owner_ids=allowed_owner_ids,
            source_types=None,
        )
        cached_answer = await get_cached_rag_answer(
            user_id=access.user_id,
            project_id=access.project_id,
            query=query,
            top_k=resolved_top_k,
            policy_revision=policy_revision,
        )
        if cached_answer is not None and chunks:
            from backend.app.modules.rag.domain.models import Citation

            citations = [
                Citation(
                    document_id=str(item.get("document_id") or ""),
                    chunk_id=str(item.get("chunk_id") or ""),
                    filename=str(item.get("filename") or ""),
                    page_number=item.get("page_number"),
                    score=float(item.get("score") or 0.0),
                    snippet=str(item.get("snippet") or ""),
                    chunk_index=int(item.get("chunk_index") or 0),
                )
                for item in cached_answer.get("citations") or []
                if isinstance(item, dict)
            ]
            return RagAnswer(
                query=query,
                answer=str(cached_answer.get("answer") or ""),
                citations=citations,
                retrieved_chunk_ids=[
                    str(chunk_id)
                    for chunk_id in (cached_answer.get("retrieved_chunk_ids") or [])
                ],
                model_name=str(cached_answer.get("model_name") or ""),
                latency_ms=int((time.perf_counter() - started) * 1000),
                no_context=False,
            )

        if not chunks:
            answer_text = (
                "No relevant document context was found in your indexed documents for this question."
            )
            result = RagAnswer(
                query=query,
                answer=answer_text,
                citations=[],
                retrieved_chunk_ids=[],
                no_context=True,
                latency_ms=int((time.perf_counter() - started) * 1000),
            )
            await self._repo.log_query(
                db,
                user_id=uuid.UUID(access.user_id),
                organization_id=uuid.UUID(access.organization_id)
                if access.organization_id
                else None,
                project_id=access.project_id,
                query=query,
                answer=answer_text,
                retrieved_chunk_ids=[],
                model_name="",
                latency_ms=result.latency_ms,
            )
            return result

        messages = self._context.build_answer_messages(
            query=query,
            chunks=chunks,
            memory_context=memory_context,
        )

        from backend.app.modules.llm.base import LLMMessage
        from backend.app.modules.llm.service import get_llm_service

        llm = get_llm_service()
        response = await llm.complete(
            "rag_answer",
            [LLMMessage(role=m["role"], content=m["content"]) for m in messages],
        )
        answer_text = (response.content or "").strip()
        citations = self._citations.build_citations(chunks)
        latency_ms = int((time.perf_counter() - started) * 1000)

        result = RagAnswer(
            query=query,
            answer=answer_text,
            citations=citations,
            retrieved_chunk_ids=[c.chunk_id for c in chunks],
            model_name=response.model or settings.LLM_MODEL,
            latency_ms=latency_ms,
        )

        await set_cached_rag_answer(
            user_id=access.user_id,
            project_id=access.project_id,
            query=query,
            top_k=resolved_top_k,
            policy_revision=policy_revision,
            payload={
                "answer": answer_text,
                "citations": [citation.to_dict() for citation in citations],
                "retrieved_chunk_ids": result.retrieved_chunk_ids,
                "model_name": result.model_name,
            },
        )

        await self._repo.log_query(
            db,
            user_id=uuid.UUID(access.user_id),
            organization_id=uuid.UUID(access.organization_id) if access.organization_id else None,
            project_id=access.project_id,
            query=query,
            answer=answer_text,
            retrieved_chunk_ids=result.retrieved_chunk_ids,
            model_name=result.model_name,
            latency_ms=latency_ms,
        )
        logger.info(
            "rag_answer user_id=%s citations=%s latency_ms=%s",
            access.user_id,
            len(citations),
            latency_ms,
        )
        return result
