from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ExerciseType(str, Enum):
    RECOGNITION = "recognition"
    RECALL = "recall"
    PRODUCTION = "production"
    FILL_BLANK = "fill_blank"
    TRANSLATION = "translation"


class QuizQuestion(BaseModel):
    id: str
    word_id: UUID | None = None
    lemma: str = ""
    exercise_type: ExerciseType
    question_type: str = "short"
    prompt: str
    options: list[str] = Field(default_factory=list)
    correct_answer: str
    explanation: str = ""
    use_ai_judge: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class QuizSession(BaseModel):
    session_id: str
    level: str
    source: str = "template"
    questions: list[QuizQuestion] = Field(default_factory=list)
