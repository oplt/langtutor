from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class NotebookEntryIn(BaseModel):
    lemma: str = Field(min_length=1, max_length=128)
    note: str = ""
    context: str = ""
    source: str = "manual"
    session_id: str | None = None


class NotebookEntryOut(BaseModel):
    id: str
    lemma: str
    note: str
    context: str
    source: str
    word_id: str | None = None
    rank: int | None = None
    level: str | None = None
    translation: str | None = None
    recognition_strength: int | None = None
    recall_strength: int | None = None
    next_review_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class NotebookListOut(BaseModel):
    entries: list[NotebookEntryOut]
    due_count: int = 0
