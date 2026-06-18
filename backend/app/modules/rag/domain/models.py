from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from backend.app.modules.rag.domain.enums import DocumentStatus, IngestionJobStatus, SourceType


@dataclass
class Document:
    id: str
    user_id: str
    organization_id: str | None
    project_id: str | None
    filename: str
    original_filename: str
    content_type: str
    storage_path: str
    status: DocumentStatus
    source_type: SourceType
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None


@dataclass
class ParsedDocument:
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentChunk:
    id: str | None
    document_id: str
    user_id: str
    organization_id: str | None
    project_id: str | None
    chunk_index: int
    content: str
    token_count: int
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None
    vector_external_id: str | None = None


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    content: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)
    filename: str = ""
    chunk_index: int = 0
    page_number: int | None = None


@dataclass
class Citation:
    document_id: str
    chunk_id: str
    filename: str
    page_number: int | None
    score: float
    snippet: str
    chunk_index: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "chunk_id": self.chunk_id,
            "filename": self.filename,
            "page_number": self.page_number,
            "score": round(self.score, 4),
            "snippet": self.snippet,
            "chunk_index": self.chunk_index,
        }


@dataclass
class RagAnswer:
    query: str
    answer: str
    citations: list[Citation] = field(default_factory=list)
    retrieved_chunk_ids: list[str] = field(default_factory=list)
    model_name: str = ""
    latency_ms: int = 0
    no_context: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "answer": self.answer,
            "citations": [c.to_dict() for c in self.citations],
            "retrieved_chunk_ids": self.retrieved_chunk_ids,
            "model_name": self.model_name,
            "latency_ms": self.latency_ms,
            "no_context": self.no_context,
        }


@dataclass
class RagQuery:
    id: str | None
    user_id: str
    organization_id: str | None
    project_id: str | None
    query: str
    answer: str
    retrieved_chunk_ids: list[str]
    model_name: str
    latency_ms: int
    created_at: datetime | None = None


@dataclass
class IngestionJob:
    id: str
    document_id: str
    user_id: str
    project_id: str | None
    status: IngestionJobStatus
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime | None = None
