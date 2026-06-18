"""Quiz application service — routes delegate here; LLM calls stay in quiz/llm.py."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.db.base import CEFRLevel
from backend.app.modules.learning.engine import ensure_words_seeded, update_word_progress
from backend.app.modules.learning.models import Word
from backend.app.modules.learning.quiz.llm import (
    generate_llm_quiz,
    grade_deterministic,
    judge_with_llm,
)
from backend.app.modules.learning.quiz.models import ExerciseType, QuizQuestion, QuizSession
from backend.app.modules.learning.quiz.templates import build_template_quiz
from backend.app.modules.memory.service import get_memory_service
from backend.app.modules.memory.types import TraceEvent

DEFAULT_EXERCISE_TYPES = [
    ExerciseType.RECOGNITION,
    ExerciseType.RECALL,
    ExerciseType.FILL_BLANK,
]


class QuizService:
    async def generate(
        self,
        db: AsyncSession,
        *,
        level: CEFRLevel,
        count: int = 5,
        exercise_types: list[ExerciseType] | None = None,
        use_llm: bool = True,
        topic: str = "",
    ) -> QuizSession:
        await ensure_words_seeded(db)
        types = exercise_types or list(DEFAULT_EXERCISE_TYPES)
        words = (
            await db.execute(
                select(Word).where(Word.level == level).order_by(Word.rank).limit(120)
            )
        ).scalars().all()
        questions: list[QuizQuestion] = []
        source = "template"
        if use_llm and settings.AI_AGENT_ENABLED:
            questions = await generate_llm_quiz(
                level=level,
                words=words,
                count=count,
                exercise_types=types,
                topic=topic,
            )
            if questions:
                source = "llm"
        if not questions:
            questions = build_template_quiz(
                words=words,
                level=level,
                count=count,
                exercise_types=types,
            )
        return QuizSession(
            session_id=str(uuid.uuid4()),
            level=level.value,
            source=source,
            questions=questions,
        )

    async def submit_answer(
        self,
        db: AsyncSession,
        *,
        user_id,
        question: QuizQuestion,
        user_answer: str,
        language: str = "en",
    ) -> dict:
        trimmed = user_answer.strip()
        if question.use_ai_judge or question.question_type == "open":
            judged = await judge_with_llm(
                prompt=question.prompt,
                question_type=question.question_type,
                correct_answer=question.correct_answer,
                explanation=question.explanation,
                user_answer=trimmed,
                options=question.options,
                language=language,
            )
            correct = judged["correct"]
            feedback = judged["feedback"]
            verdict = judged["verdict"]
        else:
            qtype = "choice" if question.question_type == "choice" else question.question_type
            correct = grade_deterministic(
                question_type=qtype,
                correct_answer=question.correct_answer,
                user_answer=trimmed,
            )
            feedback = "Correct!" if correct else f"Expected: {question.correct_answer}"
            verdict = "correct" if correct else "incorrect"

        if question.word_id:
            event = _event_for_exercise(question.exercise_type)
            await update_word_progress(
                db=db,
                user_id=user_id,
                word_id=question.word_id,
                event=event,
                correct=correct,
            )

        await self._record_quiz_memory(
            db,
            user_id=user_id,
            question=question,
            correct=correct,
        )

        return {
            "correct": correct,
            "verdict": verdict,
            "feedback": feedback,
            "word_progress_updated": question.word_id is not None,
        }

    async def judge_only(
        self,
        *,
        prompt: str,
        question_type: str,
        correct_answer: str,
        explanation: str,
        user_answer: str,
        options: list[str] | None = None,
        language: str = "en",
    ) -> dict:
        if question_type in {"choice", "short", "fill_blank"} and not _looks_open(prompt):
            correct = grade_deterministic(
                question_type="choice" if question_type == "choice" else "short",
                correct_answer=correct_answer,
                user_answer=user_answer,
            )
            return {
                "correct": correct,
                "verdict": "correct" if correct else "incorrect",
                "feedback": "Correct!" if correct else f"Expected: {correct_answer}",
            }
        return await judge_with_llm(
            prompt=prompt,
            question_type=question_type,
            correct_answer=correct_answer,
            explanation=explanation,
            user_answer=user_answer,
            options=options,
            language=language,
        )

    async def _record_quiz_memory(
        self,
        db: AsyncSession,
        *,
        user_id,
        question: QuizQuestion,
        correct: bool,
    ) -> None:
        await get_memory_service().emit(
            db,
            user_id=user_id,
            event=TraceEvent(
                surface="quiz",
                kind="quiz_answer",
                payload={
                    "lemma": question.lemma,
                    "exercise_type": question.exercise_type.value,
                    "correct": correct,
                    "prompt": question.prompt[:120],
                },
            ),
        )


def _event_for_exercise(exercise: ExerciseType) -> str:
    if exercise == ExerciseType.RECOGNITION:
        return "recognition"
    if exercise == ExerciseType.PRODUCTION:
        return "production"
    return "recall"


def _looks_open(prompt: str) -> bool:
    lowered = prompt.lower()
    return "write" in lowered or "sentence" in lowered or "produce" in lowered


_service: QuizService | None = None


def get_quiz_service() -> QuizService:
    global _service
    if _service is None:
        _service = QuizService()
    return _service
