from __future__ import annotations

from typing import Protocol

from backend.app.modules.rag.domain.models import DocumentChunk, RetrievedChunk


class VectorStoreAdapter(Protocol):
    async def upsert_chunks(self, chunks: list[DocumentChunk]) -> None: ...

    async def similarity_search(
        self,
        query_embedding: list[float],
        *,
        user_id: str,
        project_id: str | None,
        top_k: int,
        allowed_user_ids: list[str] | None = None,
        document_ids: list[str] | None = None,
    ) -> list[RetrievedChunk]: ...

    async def delete_document(self, document_id: str, user_id: str) -> None: ...
