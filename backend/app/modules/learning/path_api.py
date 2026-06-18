from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.db.base import CEFRLevel
from backend.app.modules.users.models import User
from backend.app.db.session import get_db
from backend.app.modules.auth.dependencies import get_current_user
from backend.app.modules.learning.mastery.runtime import get_mastery_runtime
from backend.app.modules.learning.mastery.schemas import (
    PathAssessIn,
    PathDrillOut,
    PathGradeIn,
    PathGradeOut,
    PathMapOut,
    PathQuizIn,
)
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/learning/path", tags=["learning-path"])


@router.get("/{level}/map", response_model=PathMapOut)
async def path_map(
    level: CEFRLevel,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    runtime = get_mastery_runtime()
    try:
        payload = await runtime.get_map(db, user_id=user.id, level=level)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PathMapOut.model_validate(payload)


@router.get("/{level}/next")
async def path_next(
    level: CEFRLevel,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    runtime = get_mastery_runtime()
    try:
        return await runtime.get_next(db, user_id=user.id, level=level)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{level}/quiz")
async def path_register_quiz(
    level: CEFRLevel,
    payload: PathQuizIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    runtime = get_mastery_runtime()
    try:
        return await runtime.register_quiz(
            db,
            user_id=user.id,
            level=level,
            knowledge_point_id=payload.knowledge_point_id,
            prompt=payload.prompt,
            expected_answer=payload.expected_answer,
            question_type=payload.question_type,
            options=payload.options,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{level}/grade", response_model=PathGradeOut)
async def path_grade(
    level: CEFRLevel,
    body: PathGradeIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    runtime = get_mastery_runtime()
    try:
        result = await runtime.grade_answer(
            db, user_id=user.id, level=level, user_answer=body.answer
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PathGradeOut.model_validate(result)


@router.post("/{level}/assess")
async def path_assess(
    level: CEFRLevel,
    payload: PathAssessIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    runtime = get_mastery_runtime()
    return await runtime.assess_qualitative(
        db,
        user_id=user.id,
        level=level,
        knowledge_point_id=payload.knowledge_point_id,
        passed=payload.passed,
        evidence=payload.evidence,
    )


@router.get("/{level}/drill", response_model=PathDrillOut)
async def path_drill(
    level: CEFRLevel,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    runtime = get_mastery_runtime()
    try:
        payload = await runtime.build_drill(db, user_id=user.id, level=level)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PathDrillOut.model_validate(payload)


@router.get("/review-queue")
async def review_queue(
    level: CEFRLevel = Query(default=CEFRLevel.A1),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from backend.app.modules.learning.mastery.policy import due_reviews, map_summary

    runtime = get_mastery_runtime()
    _, progress = await runtime.ensure_path(db, user_id=user.id, level=level)
    due = due_reviews(progress)
    return {
        "level": level.value,
        "due_count": len(due),
        "tasks": [
            {
                "knowledge_point_id": task.knowledge_point_id,
                "due_at": task.due_at,
                "priority": task.priority,
            }
            for task in due[:10]
        ],
        "map": map_summary(progress),
    }
