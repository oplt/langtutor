from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.base import CEFRLevel
from backend.app.modules.users.models import User
from backend.app.modules.book.compiler import find_page_outline, get_lesson_compiler, load_book_spine
from backend.app.modules.book.models import LessonBook, LessonPage
from backend.app.modules.learning.models import UserLessonPageProgress


class LessonBookService:
    async def list_books(self) -> list[LessonBook]:
        books: list[LessonBook] = []
        for level in CEFRLevel:
            try:
                books.append(load_book_spine(level))
            except FileNotFoundError:
                continue
        return books

    async def get_book(self, level: CEFRLevel) -> LessonBook:
        return load_book_spine(level)

    async def get_page(
        self,
        db: AsyncSession,
        *,
        level: CEFRLevel,
        page_id: str,
    ) -> LessonPage:
        compiler = get_lesson_compiler()
        return await compiler.compile_page(db, level=level, page_id=page_id)

    async def get_progress(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        level: CEFRLevel | None = None,
    ) -> list[dict[str, Any]]:
        query = select(UserLessonPageProgress).where(UserLessonPageProgress.user_id == user_id)
        if level is not None:
            query = query.where(UserLessonPageProgress.level == level)
        rows = (await db.execute(query.order_by(UserLessonPageProgress.completed_at.desc()))).scalars().all()
        return [
            {
                "page_id": row.page_id,
                "level": row.level.value,
                "quiz_score": row.quiz_score,
                "completed_at": row.completed_at.isoformat(),
            }
            for row in rows
        ]

    async def mark_complete(
        self,
        db: AsyncSession,
        *,
        user: User,
        level: CEFRLevel,
        page_id: str,
        quiz_score: float | None = None,
    ) -> dict[str, Any]:
        book = load_book_spine(level)
        find_page_outline(book, page_id)

        row = (
            await db.execute(
                select(UserLessonPageProgress)
                .where(UserLessonPageProgress.user_id == user.id)
                .where(UserLessonPageProgress.page_id == page_id)
            )
        ).scalar_one_or_none()

        now = datetime.now(timezone.utc)
        if row is None:
            row = UserLessonPageProgress(
                user_id=user.id,
                level=level,
                page_id=page_id,
                quiz_score=quiz_score,
                completed_at=now,
            )
            db.add(row)
        else:
            row.quiz_score = quiz_score if quiz_score is not None else row.quiz_score
            row.completed_at = now

        await db.commit()
        await db.refresh(row)
        return {
            "page_id": row.page_id,
            "level": row.level.value,
            "quiz_score": row.quiz_score,
            "completed_at": row.completed_at.isoformat(),
        }


_service: LessonBookService | None = None


def get_lesson_book_service() -> LessonBookService:
    global _service
    if _service is None:
        _service = LessonBookService()
    return _service
