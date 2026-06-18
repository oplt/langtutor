from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DocumentOut(BaseModel):
    id: str
    user_id: str
    organization_id: str | None = None
    project_id: str | None = None
    filename: str
    original_filename: str
    content_type: str
    status: str
    source_type: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ChunkOut(BaseModel):
    id: str
    chunk_index: int
    content: str
    token_count: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class JobOut(BaseModel):
    id: str
    document_id: str
    status: str
    progress_stage: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class RetrieveIn(BaseModel):
    query: str = Field(min_length=1, max_length=8000)
    project_id: str | None = None
    top_k: int | None = Field(default=None, ge=1, le=20)
    document_ids: list[str] | None = None


class RetrievedChunkOut(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    content: str
    score: float
    chunk_index: int
    page_number: int | None = None


class CitationOut(BaseModel):
    document_id: str
    chunk_id: str
    filename: str
    page_number: int | None
    score: float
    snippet: str
    chunk_index: int


class AskIn(BaseModel):
    query: str = Field(min_length=1, max_length=8000)
    project_id: str | None = None
    top_k: int | None = Field(default=None, ge=1, le=20)


class AskOut(BaseModel):
    query: str
    answer: str
    citations: list[CitationOut]
    retrieved_chunk_ids: list[str]
    model_name: str
    latency_ms: int
    no_context: bool = False


class QueryLogOut(BaseModel):
    id: str
    query: str
    answer: str
    model_name: str
    latency_ms: int
    created_at: datetime | None = None
