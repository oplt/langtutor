from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from backend.app.db.base import CEFRLevel


class PathQuizIn(BaseModel):
    knowledge_point_id: str
    prompt: str
    expected_answer: str
    question_type: str = "short"
    options: list[str] = Field(default_factory=list)


class PathGradeIn(BaseModel):
    answer: str = Field(min_length=1, max_length=2000)


class PathAssessIn(BaseModel):
    knowledge_point_id: str
    passed: bool
    evidence: str = ""


class PathMapOut(BaseModel):
    level: CEFRLevel
    next: dict[str, Any]
    map: dict[str, Any]
    version: int


class PathDrillOut(BaseModel):
    step: dict[str, Any]
    drill: Optional[dict[str, Any]] = None


class PathGradeOut(BaseModel):
    correct: bool
    map: PathMapOut
    drill: PathDrillOut
