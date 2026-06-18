from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import delete, select
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
        for chunk in chunks:
            row = RagChunk(
                id=uuid.UUID(chunk.id) if chunk.id else uuid.uuid4(),
                document_id=uuid.UUID(chunk.document_id),
                user_id=uuid.UUID(chunk.user_id),
                organization_id=uuid.UUID(chunk.organization_id) if chunk.organization_id else None,
                project_id=chunk.project_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                token_count=chunk.token_count,
                metadata_json=chunk.metadata,
                embedding=chunk.embedding,
                vector_external_id=chunk.vector_external_id,
            )
            self.db.add(row)
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
