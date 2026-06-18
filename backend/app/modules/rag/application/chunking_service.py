from __future__ import annotations

from backend.app.modules.rag.domain.models import DocumentChunk, ParsedDocument
from backend.app.modules.rag.infrastructure.langchain_text_splitters import split_documents


class ChunkingService:
    async def chunk(
        self,
        documents: list[ParsedDocument],
        *,
        document_id: str,
        user_id: str,
        organization_id: str | None,
        project_id: str | None,
        filename: str,
        source_type: str,
    ) -> list[DocumentChunk]:
        return split_documents(
            documents,
            document_id=document_id,
            user_id=user_id,
            organization_id=organization_id,
            project_id=project_id,
            filename=filename,
            source_type=source_type,
        )
