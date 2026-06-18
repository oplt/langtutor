from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.modules.users.models import User
from backend.app.db.session import get_db
from backend.app.modules.auth.dependencies import get_current_user
from backend.app.modules.notebook.schemas import NotebookEntryIn, NotebookEntryOut, NotebookListOut
from backend.app.modules.notebook.service import get_notebook_service

router = APIRouter(prefix="/api/notebook", tags=["notebook"])


@router.get("/entries", response_model=NotebookListOut)
async def list_entries(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = get_notebook_service()
    entries = await service.list_entries(db, user_id=user.id)
    due_count = sum(1 for item in entries if item.get("due"))
    return NotebookListOut(
        entries=[NotebookEntryOut(**{k: v for k, v in item.items() if k != "due"}) for item in entries],
        due_count=due_count,
    )


@router.post("/entries", response_model=NotebookEntryOut)
async def save_entry(
    payload: NotebookEntryIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = get_notebook_service()
    try:
        row = await service.save_entry(
            db,
            user_id=user.id,
            lemma=payload.lemma,
            note=payload.note,
            context=payload.context,
            source=payload.source,
            session_id=payload.session_id,
        )
        await db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    entries = await service.list_entries(db, user_id=user.id)
    match = next((item for item in entries if item["id"] == str(row.id)), None)
    if match is None:
        raise HTTPException(status_code=500, detail="entry_not_found_after_save")
    return NotebookEntryOut(**{k: v for k, v in match.items() if k != "due"})


@router.delete("/entries/{entry_id}")
async def delete_entry(
    entry_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = get_notebook_service()
    deleted = await service.delete_entry(db, user_id=user.id, entry_id=entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="entry_not_found")
    await db.commit()
    return {"ok": True}
