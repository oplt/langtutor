from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class KnowledgeBaseCreateIn(BaseModel):
    name: str
    description: str = ""


class KnowledgeBaseOut(BaseModel):
    id: str
    name: str
    description: str
    stats: dict[str, Any] = Field(default_factory=dict)


class KnowledgeSearchIn(BaseModel):
    kb_name: str = "dutch-core"
    query: str
    top_k: int = 5


class KnowledgeIngestIn(BaseModel):
    paths: list[str] = Field(min_length=1)


class KnowledgeSourceOut(BaseModel):
    chunk_id: str
    score: float
    title: str
    source: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeSearchOut(BaseModel):
    query: str
    kb_name: str
    sources: list[KnowledgeSourceOut]
