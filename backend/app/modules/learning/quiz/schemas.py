from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from backend.app.db.base import CEFRLevel
from backend.app.modules.learning.quiz.models import ExerciseType, QuizQuestion, QuizSession


class QuizGenerateIn(BaseModel):
    level: CEFRLevel = CEFRLevel.A1
    count: int = Field(default=5, ge=1, le=15)
    exercise_types: list[ExerciseType] = Field(
        default_factory=lambda: [
            ExerciseType.RECOGNITION,
            ExerciseType.RECALL,
            ExerciseType.FILL_BLANK,
        ]
    )
    use_llm: bool = True
    topic: str = ""


class QuizJudgeIn(BaseModel):
    prompt: str
    question_type: str = "short"
    correct_answer: str
    explanation: str = ""
    user_answer: str
    options: list[str] = Field(default_factory=list)
    language: str = "en"


class QuizSubmitIn(BaseModel):
    question: QuizQuestion
    user_answer: str = Field(min_length=0, max_length=4000)
    language: str = "en"


class QuizJudgeOut(BaseModel):
    correct: bool
    verdict: Literal["correct", "partial", "incorrect"]
    feedback: str


class QuizSubmitOut(QuizJudgeOut):
    word_progress_updated: bool = False
