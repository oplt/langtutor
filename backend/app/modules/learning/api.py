from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.modules.auth.dependencies import get_current_user
from backend.app.shared.schemas import (
    LevelInfo,
    ProgressSummary,
    StoryGenerateIn,
    StoryOut,
    WordOut,
    WordProgressUpdateIn,
    LevelProgress,
)
from backend.app.db.base import CEFRLevel
from backend.app.db.session import get_db
from backend.app.modules.learning.models import UserWordProgress, Word
from backend.app.modules.stories.models import Story, StoryWord
from backend.app.modules.users.models import User
from backend.app.modules.learning.engine import (
    ensure_words_seeded,
    generate_story,
    get_level_definitions,
    level_counts,
    update_word_progress,
)
from backend.app.modules.learning.response_cache import (
    get_cached_levels,
    get_cached_progress_summary,
    invalidate_levels_cache,
    invalidate_progress_summary,
    set_cached_levels,
    set_cached_progress_summary,
)


router = APIRouter(prefix="/api/learning", tags=["learning"])


async def build_levels_payload(db: AsyncSession) -> dict:
    await ensure_words_seeded(db)
    counts = await level_counts(db)
    levels = []
    for definition in get_level_definitions():
        level = definition["level"]
        levels.append(
            LevelInfo(
                level=level,
                rank_min=definition["rank_min"],
                rank_max=definition["rank_max"],
                word_coverage=definition["word_coverage"],
                grammar_focus=definition["grammar_focus"],
                input_type=definition["input_type"],
                word_count=counts.get(level, 0),
            )
        )
    total_words = sum(counts.values())
    return {
        "levels": [item.model_dump(mode="json") for item in levels],
        "total_words": total_words,
    }


def _apply_levels_cache_headers(response: Response) -> None:
    from backend.app.core.config import settings

    response.headers["Cache-Control"] = (
        f"public, max-age={settings.LEARNING_LEVELS_CACHE_TTL_SECONDS}"
    )


@router.get("/levels")
async def get_levels(
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    cached = await get_cached_levels()
    if cached is not None:
        _apply_levels_cache_headers(response)
        return cached

    payload = await build_levels_payload(db)
    await set_cached_levels(payload)
    _apply_levels_cache_headers(response)
    return payload


@router.get("/words")
async def list_words(
    level: Optional[CEFRLevel] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    search: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    await ensure_words_seeded(db)
    q = select(Word)
    if level:
        q = q.where(Word.level == level)
    if search:
        q = q.where(Word.lemma.ilike(f"%{search.strip().lower()}%"))
    q = q.order_by(Word.rank).offset(offset).limit(limit)
    result = await db.execute(q)
    items = result.scalars().all()
    return {"items": [WordOut.model_validate(item) for item in items]}


@router.post("/stories/generate", response_model=StoryOut)
async def generate_story_route(
    payload: StoryGenerateIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = user
    package = await generate_story(
        db=db,
        level=payload.level,
        target_word_count=payload.target_word_count,
        max_words=payload.max_words,
    )
    target_words = [w.lemma for w in package.new_words + package.review_words]
    return StoryOut(
        id=package.story.id,
        level=package.story.level,
        title=package.story.title,
        body=package.story.body,
        word_count=package.story.word_count,
        new_word_count=package.story.new_word_count,
        new_words=[w.lemma for w in package.new_words],
        review_words=[w.lemma for w in package.review_words],
        target_words=target_words,
    )


@router.get("/stories/{story_id}", response_model=StoryOut)
async def get_story(
    story_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = user
    try:
        story_uuid = UUID(story_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid story id") from exc
    story = (
        await db.execute(
            select(Story).where(Story.id == story_uuid)
        )
    ).scalar_one_or_none()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    words = (
        await db.execute(
            select(Word.lemma, StoryWord.is_new)
            .join(StoryWord, StoryWord.word_id == Word.id)
            .where(StoryWord.story_id == story.id)
            .order_by(StoryWord.position)
        )
    ).all()
    new_words = [w for w, is_new in words if is_new]
    review_words = [w for w, is_new in words if not is_new]
    target_words = [w for w, _ in words]

    return StoryOut(
        id=story.id,
        level=story.level,
        title=story.title,
        body=story.body,
        word_count=story.word_count,
        new_word_count=story.new_word_count,
        new_words=new_words,
        review_words=review_words,
        target_words=target_words,
    )


@router.post("/progress/word")
async def update_progress(
    payload: WordProgressUpdateIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = user.id
    await ensure_words_seeded(db)
    progress = await update_word_progress(
        db=db,
        user_id=user_id,
        word_id=payload.word_id,
        event=payload.event,
        correct=payload.correct,
    )
    await invalidate_progress_summary(user_id)
    return {
        "ok": True,
        "next_review_at": progress.next_review_at,
        "recognition_strength": progress.recognition_strength,
        "recall_strength": progress.recall_strength,
        "production_strength": progress.production_strength,
    }


@router.get("/progress/summary", response_model=ProgressSummary)
async def progress_summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = user.id
    cached = await get_cached_progress_summary(user_id)
    if cached is not None:
        return ProgressSummary.model_validate(cached)

    await ensure_words_seeded(db)
    mastery_threshold = 60

    total_words = (
        await db.execute(select(func.count(Word.id)))
    ).scalar_one() or 0

    mastered_counts = (
        await db.execute(
            select(Word.level, func.count(Word.id))
            .join(UserWordProgress, UserWordProgress.word_id == Word.id)
            .where(UserWordProgress.user_id == user_id)
            .where(UserWordProgress.recognition_strength >= mastery_threshold)
            .where(UserWordProgress.recall_strength >= mastery_threshold)
            .group_by(Word.level)
        )
    ).all()
    mastered_by_level = {level: count for level, count in mastered_counts}

    total_by_level = await level_counts(db)
    levels = [
        LevelProgress(
            level=level,
            mastered=mastered_by_level.get(level, 0),
            total=total_by_level.get(level, 0),
        )
        for level in total_by_level.keys()
    ]

    mastered_words = sum(mastered_by_level.values())

    next_review_at = (
        await db.execute(
            select(func.min(UserWordProgress.next_review_at))
            .where(UserWordProgress.user_id == user_id)
        )
    ).scalar_one_or_none()

    summary = ProgressSummary(
        total_words=total_words,
        mastered_words=mastered_words,
        next_review_at=next_review_at,
        levels=levels,
    )
    await set_cached_progress_summary(user_id, summary.model_dump(mode="json"))
    return summary
