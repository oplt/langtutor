from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.modules.rag.domain.models import DocumentChunk, RetrievedChunk
from backend.app.modules.rag.infrastructure.sqlalchemy_models import RagChunk, RagDocument

logger = logging.getLogger(__name__)


class PgvectorAdapter:
    """Vector store backed by rag_chunks.embedding (native pgvector cosine search)."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def upsert_chunks(self, chunks: list[DocumentChunk]) -> None:
        if not chunks:
            return
        rows = [
            {
                "id": uuid.UUID(chunk.id) if chunk.id else uuid.uuid4(),
                "document_id": uuid.UUID(chunk.document_id),
                "user_id": uuid.UUID(chunk.user_id),
                "organization_id": uuid.UUID(chunk.organization_id) if chunk.organization_id else None,
                "project_id": chunk.project_id,
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
                "token_count": chunk.token_count,
                "metadata_json": chunk.metadata,
                "embedding": chunk.embedding,
                "vector_external_id": chunk.vector_external_id,
            }
            for chunk in chunks
        ]
        await self.db.execute(insert(RagChunk), rows)
        await self.db.flush()

    async def similarity_search(
        self,
        query_embedding: list[float],
        *,
        user_id: str,
        project_id: str | None,
        top_k: int,
        allowed_user_ids: list[str] | None = None,
        document_ids: list[str] | None = None,
        source_types: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        owner_ids = allowed_user_ids or [user_id]
        owner_uuid = [uuid.UUID(item) for item in owner_ids]

        # pgvector <=> is cosine distance (0 = identical). Similarity = 1 - distance.
        distance_expr = RagChunk.embedding.cosine_distance(query_embedding)
        score_expr = (1.0 - distance_expr).label("score")
        max_distance = 1.0 - settings.RAG_SCORE_THRESHOLD

        stmt = (
            select(RagChunk, RagDocument, score_expr)
            .join(RagDocument, RagDocument.id == RagChunk.document_id)
            .where(RagDocument.deleted_at.is_(None))
            .where(RagDocument.status == "indexed")
            .where(RagChunk.user_id.in_(owner_uuid))
            .where(RagChunk.embedding.is_not(None))
            .where(distance_expr <= max_distance)
        )
        if project_id is not None:
            stmt = stmt.where(RagChunk.project_id == project_id)
        if document_ids:
            stmt = stmt.where(RagChunk.document_id.in_([uuid.UUID(d) for d in document_ids]))
        if source_types:
            stmt = stmt.where(RagDocument.source_type.in_(source_types))

        stmt = stmt.order_by(distance_expr.asc()).limit(max(1, top_k))

        rows = (await self.db.execute(stmt)).all()
        results: list[RetrievedChunk] = []
        for chunk_row, doc_row, score in rows:
            meta = chunk_row.metadata_json or {}
            results.append(
                RetrievedChunk(
                    chunk_id=str(chunk_row.id),
                    document_id=str(chunk_row.document_id),
                    content=chunk_row.content,
                    score=float(score),
                    metadata=meta,
                    filename=doc_row.original_filename,
                    chunk_index=chunk_row.chunk_index,
                    page_number=meta.get("page_number"),
                )
            )
        return results

    async def lexical_search(
        self,
        query: str,
        *,
        user_id: str,
        project_id: str | None,
        top_k: int,
        allowed_user_ids: list[str] | None = None,
        document_ids: list[str] | None = None,
        source_types: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        from backend.app.modules.knowledge.bm25 import bm25_score, tokenize

        terms = [term for term in tokenize(query) if len(term) >= 3][:12]
        if not terms:
            return []

        owner_ids = allowed_user_ids or [user_id]
        owner_uuid = [uuid.UUID(item) for item in owner_ids]
        term_filters = [RagChunk.content.ilike(f"%{term}%") for term in terms[:6]]

        stmt = (
            select(RagChunk, RagDocument)
            .join(RagDocument, RagDocument.id == RagChunk.document_id)
            .where(RagDocument.deleted_at.is_(None))
            .where(RagDocument.status == "indexed")
            .where(RagChunk.user_id.in_(owner_uuid))
            .where(or_(*term_filters))
        )
        if project_id is not None:
            stmt = stmt.where(RagChunk.project_id == project_id)
        if document_ids:
            stmt = stmt.where(RagChunk.document_id.in_([uuid.UUID(d) for d in document_ids]))
        if source_types:
            stmt = stmt.where(RagDocument.source_type.in_(source_types))

        rows = (await self.db.execute(stmt.limit(max(20, top_k * 6)))).all()
        if not rows:
            return []

        doc_freq: dict[str, int] = {}
        prepared: list[tuple[Any, Any, dict[str, int], int]] = []
        total_len = 0
        for chunk_row, doc_row in rows:
            from backend.app.modules.knowledge.bm25 import term_frequencies

            term_freqs, doc_len = term_frequencies(chunk_row.content or "")
            total_len += doc_len
            for term in term_freqs:
                doc_freq[term] = doc_freq.get(term, 0) + 1
            prepared.append((chunk_row, doc_row, term_freqs, doc_len))

        doc_count = len(prepared)
        avg_doc_len = total_len / max(doc_count, 1)
        scored: list[RetrievedChunk] = []
        for chunk_row, doc_row, term_freqs, doc_len in prepared:
            score = bm25_score(
                query_terms=terms,
                term_freqs=term_freqs,
                doc_len=doc_len,
                avg_doc_len=avg_doc_len,
                doc_count=doc_count,
                doc_freq=doc_freq,
            )
            if score <= 0:
                continue
            meta = chunk_row.metadata_json or {}
            scored.append(
                RetrievedChunk(
                    chunk_id=str(chunk_row.id),
                    document_id=str(chunk_row.document_id),
                    content=chunk_row.content,
                    score=min(1.0, score / 8.0),
                    metadata=meta,
                    filename=doc_row.original_filename,
                    chunk_index=chunk_row.chunk_index,
                    page_number=meta.get("page_number"),
                )
            )
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[: max(1, top_k)]

    async def delete_document(self, document_id: str, user_id: str) -> None:
        await self.db.execute(
            delete(RagChunk)
            .where(RagChunk.document_id == uuid.UUID(document_id))
            .where(RagChunk.user_id == uuid.UUID(user_id))
        )
        await self.db.flush()


def get_vector_store(db: AsyncSession) -> PgvectorAdapter:
    backend = settings.RAG_VECTOR_BACKEND.lower()
    if backend != "pgvector":
        raise ValueError(
            f"Unsupported RAG_VECTOR_BACKEND={settings.RAG_VECTOR_BACKEND!r}; "
            "only 'pgvector' is supported."
        )
    return PgvectorAdapter(db)
