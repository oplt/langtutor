from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.base import CEFRLevel
from backend.app.modules.users.models import User
from backend.app.db.session import get_db
from backend.app.modules.auth.dependencies import get_current_user
from backend.app.modules.book.schemas import LessonBookOut, LessonCompleteIn, LessonPageOut
from backend.app.modules.book.service import get_lesson_book_service


router = APIRouter(prefix="/api/book", tags=["book"])


@router.get("/levels")
async def list_books():
    service = get_lesson_book_service()
    books = await service.list_books()
    return {"books": [LessonBookOut.from_book(book) for book in books]}


@router.get("/progress")
async def get_progress(
    level: CEFRLevel | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = get_lesson_book_service()
    rows = await service.get_progress(db, user_id=user.id, level=level)
    return {"completed_pages": rows}


@router.get("/{level}")
async def get_book(level: CEFRLevel):
    service = get_lesson_book_service()
    try:
        book = await service.get_book(level)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return LessonBookOut.from_book(book)


@router.get("/{level}/pages/{page_id}")
async def get_page(
    level: CEFRLevel,
    page_id: str,
    db: AsyncSession = Depends(get_db),
):
    service = get_lesson_book_service()
    try:
        page = await service.get_page(db, level=level, page_id=page_id)
    except (FileNotFoundError, KeyError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return LessonPageOut.from_page(page)


@router.post("/{level}/pages/{page_id}/complete")
async def complete_page(
    level: CEFRLevel,
    page_id: str,
    body: LessonCompleteIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = get_lesson_book_service()
    try:
        result = await service.mark_complete(
            db,
            user=user,
            level=level,
            page_id=page_id,
            quiz_score=body.quiz_score,
        )
    except (FileNotFoundError, KeyError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return result
