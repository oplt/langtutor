"""LangChain text splitters — infrastructure only."""

from __future__ import annotations

from backend.app.core.config import settings
from backend.app.modules.rag.domain.models import DocumentChunk, ParsedDocument


def split_documents(
    documents: list[ParsedDocument],
    *,
    document_id: str,
    user_id: str,
    organization_id: str | None,
    project_id: str | None,
    filename: str,
    source_type: str,
) -> list[DocumentChunk]:
    splitter = _build_splitter()
    chunks: list[DocumentChunk] = []
    chunk_index = 0
    for doc in documents:
        parts = splitter(doc.content)
        page_number = doc.metadata.get("page")
        heading = doc.metadata.get("heading") or doc.metadata.get("title")
        for part in parts:
            if not part.strip():
                continue
            metadata = {
                "document_id": document_id,
                "user_id": user_id,
                "organization_id": organization_id,
                "project_id": project_id,
                "filename": filename,
                "chunk_index": chunk_index,
                "page_number": page_number,
                "source_type": source_type,
            }
            if heading:
                metadata["heading"] = heading
            chunks.append(
                DocumentChunk(
                    id=None,
                    document_id=document_id,
                    user_id=user_id,
                    organization_id=organization_id,
                    project_id=project_id,
                    chunk_index=chunk_index,
                    content=part.strip(),
                    token_count=_estimate_tokens(part),
                    metadata=metadata,
                )
            )
            chunk_index += 1
    return chunks


def _build_splitter():
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.RAG_CHUNK_SIZE,
            chunk_overlap=settings.RAG_CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " "],
        )
        return splitter.split_text
    except ImportError:
        return _fallback_split


def _fallback_split(text: str) -> list[str]:
    size = settings.RAG_CHUNK_SIZE
    overlap = settings.RAG_CHUNK_OVERLAP
    if len(text) <= size:
        return [text]
    parts: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        parts.append(text[start:end])
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return parts


def _estimate_tokens(text: str) -> int:
    return max(1, len(text.split()))
