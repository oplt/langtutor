from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.modules.users.models import User
from backend.app.db.session import get_db
from backend.app.modules.auth.dependencies import get_current_user
from backend.app.modules.learning.quiz.models import QuizSession
from backend.app.modules.learning.quiz.schemas import (
    QuizGenerateIn,
    QuizJudgeIn,
    QuizJudgeOut,
    QuizSubmitIn,
    QuizSubmitOut,
)
from backend.app.deps import quiz_service_dep
from backend.app.modules.learning.quiz.service import QuizService

router = APIRouter(prefix="/api/learning/quiz", tags=["learning-quiz"])


@router.post("/generate", response_model=QuizSession)
async def generate_quiz(
    payload: QuizGenerateIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: QuizService = Depends(quiz_service_dep),
):
    _ = user
    return await service.generate(
        db,
        level=payload.level,
        count=payload.count,
        exercise_types=payload.exercise_types,
        use_llm=payload.use_llm,
        topic=payload.topic,
    )


@router.post("/judge", response_model=QuizJudgeOut)
async def judge_quiz_answer(
    payload: QuizJudgeIn,
    user: User = Depends(get_current_user),
    service: QuizService = Depends(quiz_service_dep),
):
    _ = user
    result = await service.judge_only(
        prompt=payload.prompt,
        question_type=payload.question_type,
        correct_answer=payload.correct_answer,
        explanation=payload.explanation,
        user_answer=payload.user_answer,
        options=payload.options,
        language=payload.language,
    )
    return QuizJudgeOut.model_validate(result)


@router.post("/submit", response_model=QuizSubmitOut)
async def submit_quiz_answer(
    payload: QuizSubmitIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: QuizService = Depends(quiz_service_dep),
):
    result = await service.submit_answer(
        db,
        user_id=user.id,
        question=payload.question,
        user_answer=payload.user_answer,
        language=payload.language,
    )
    return QuizSubmitOut.model_validate(result)
