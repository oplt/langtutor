from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from backend.app.db.base import CEFRLevel
from backend.app.modules.users.models import User
from backend.app.db.session import get_db
from backend.app.modules.auth.dependencies import get_current_user
from backend.app.modules.extensions.classroom.service import get_classroom_service
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/extensions/classroom", tags=["extensions-classroom"])


class ClassroomGrantIn(BaseModel):
    student_email: EmailStr
    assigned_level: CEFRLevel | None = None
    note: str | None = Field(default=None, max_length=500)


@router.get("/students")
async def list_students(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = get_classroom_service()
    return await service.list_students(db, teacher_id=user.id)


@router.get("/teachers")
async def list_teachers(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = get_classroom_service()
    return await service.list_teachers_for_student(db, student_id=user.id)


@router.post("/grants")
async def create_grant(
    payload: ClassroomGrantIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = get_classroom_service()
    try:
        grant = await service.grant_student(
            db,
            teacher_id=user.id,
            student_email=str(payload.student_email),
            assigned_level=payload.assigned_level,
            note=payload.note,
        )
        await db.commit()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "grant_id": str(grant.id),
        "student_id": str(grant.student_id),
        "assigned_level": grant.assigned_level.value if grant.assigned_level else None,
    }


@router.delete("/grants/{grant_id}")
async def revoke_grant(
    grant_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = get_classroom_service()
    ok = await service.revoke_grant(db, teacher_id=user.id, grant_id=grant_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Grant not found")
    await db.commit()
    return {"ok": True}
