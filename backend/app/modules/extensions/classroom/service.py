from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from backend.app.db.base import CEFRLevel
from backend.app.modules.extensions.classroom.models import ClassroomGrant
from backend.app.modules.users.models import User


class ClassroomService:
    async def grant_student(
        self,
        db: AsyncSession,
        *,
        teacher_id: uuid.UUID,
        student_email: str,
        assigned_level: CEFRLevel | None = None,
        note: str | None = None,
    ) -> ClassroomGrant:
        student = (
            await db.execute(
                select(User).where(User.email == student_email.strip().lower())
            )
        ).scalar_one_or_none()
        if student is None:
            raise LookupError("Student account not found")
        if student.id == teacher_id:
            raise ValueError("Cannot grant yourself as a student")

        existing = (
            await db.execute(
                select(ClassroomGrant)
                .where(ClassroomGrant.teacher_id == teacher_id)
                .where(ClassroomGrant.student_id == student.id)
            )
        ).scalar_one_or_none()
        if existing is not None:
            existing.assigned_level = assigned_level
            existing.note = note
            await db.flush()
            return existing

        row = ClassroomGrant(
            teacher_id=teacher_id,
            student_id=student.id,
            assigned_level=assigned_level,
            note=note,
        )
        db.add(row)
        await db.flush()
        return row

    async def list_students(
        self, db: AsyncSession, *, teacher_id: uuid.UUID
    ) -> list[dict]:
        student = aliased(User)
        rows = (
            await db.execute(
                select(ClassroomGrant, student)
                .join(student, ClassroomGrant.student_id == student.id)
                .where(ClassroomGrant.teacher_id == teacher_id)
                .order_by(ClassroomGrant.created_at.desc())
            )
        ).all()
        payload: list[dict] = []
        for grant, user in rows:
            payload.append(
                {
                    "grant_id": str(grant.id),
                    "student_id": str(user.id),
                    "student_email": user.email,
                    "student_name": user.full_name,
                    "assigned_level": (
                        grant.assigned_level.value
                        if grant.assigned_level is not None
                        else None
                    ),
                    "note": grant.note,
                    "created_at": grant.created_at.isoformat() if grant.created_at else None,
                }
            )
        return payload

    async def list_teachers_for_student(
        self, db: AsyncSession, *, student_id: uuid.UUID
    ) -> list[dict]:
        teacher = aliased(User)
        rows = (
            await db.execute(
                select(ClassroomGrant, teacher)
                .join(teacher, ClassroomGrant.teacher_id == teacher.id)
                .where(ClassroomGrant.student_id == student_id)
            )
        ).all()
        return [
            {
                "grant_id": str(grant.id),
                "teacher_id": str(user.id),
                "teacher_email": user.email,
                "assigned_level": (
                    grant.assigned_level.value if grant.assigned_level else None
                ),
            }
            for grant, user in rows
        ]

    async def revoke_grant(
        self, db: AsyncSession, *, teacher_id: uuid.UUID, grant_id: uuid.UUID
    ) -> bool:
        row = (
            await db.execute(
                select(ClassroomGrant)
                .where(ClassroomGrant.id == grant_id)
                .where(ClassroomGrant.teacher_id == teacher_id)
            )
        ).scalar_one_or_none()
        if row is None:
            return False
        await db.delete(row)
        await db.flush()
        return True


_service: ClassroomService | None = None


def get_classroom_service() -> ClassroomService:
    global _service
    if _service is None:
        _service = ClassroomService()
    return _service
