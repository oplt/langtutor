from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from backend.app.db.base import CEFRLevel


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ErrorPayload(BaseModel):
    code: str = Field(..., min_length=1, max_length=64)
    message: str = Field(..., min_length=1, max_length=1024)
    status_code: Optional[int] = Field(default=None, ge=100, le=599)
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    ok: bool = Field(default=False)
    error: ErrorPayload
    request_id: Optional[str] = None


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: Optional[str] = Field(default=None, max_length=255)


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=255)
    is_active: Optional[bool] = None


class UserOut(ORMBase):
    id: UUID
    email: EmailStr
    full_name: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    native_language: Optional[str] = None
    target_language: Optional[str] = None
    cefr_goal: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class LevelInfo(BaseModel):
    level: CEFRLevel
    rank_min: int
    rank_max: int
    word_coverage: str
    grammar_focus: str
    input_type: str
    word_count: int


class WordOut(ORMBase):
    id: UUID
    lemma: str
    rank: int
    level: CEFRLevel


class StoryGenerateIn(BaseModel):
    level: CEFRLevel = Field(default=CEFRLevel.A1)
    target_word_count: int = Field(default=10, ge=5, le=20)
    max_words: int = Field(default=180, ge=80, le=350)


class StoryOut(ORMBase):
    id: UUID
    level: CEFRLevel
    title: str
    body: str
    word_count: int
    new_word_count: int
    new_words: List[str] = Field(default_factory=list)
    review_words: List[str] = Field(default_factory=list)
    target_words: List[str] = Field(default_factory=list)


class WordProgressUpdateIn(BaseModel):
    word_id: UUID
    event: Literal["recognition", "recall", "production"]
    correct: bool = True


class LevelProgress(BaseModel):
    level: CEFRLevel
    mastered: int
    total: int


class ProgressSummary(BaseModel):
    total_words: int
    mastered_words: int
    next_review_at: Optional[datetime] = None
    levels: List[LevelProgress] = Field(default_factory=list)
