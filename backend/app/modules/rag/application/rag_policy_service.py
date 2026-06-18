from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.modules.extensions.classroom.models import ClassroomGrant
from backend.app.modules.rag.domain.value_objects import AccessContext
from backend.app.modules.rag.infrastructure.repositories import RagRepository, get_rag_repository
from backend.app.modules.rag.infrastructure.sqlalchemy_models import RagDocument


class RagPolicyService:
    def __init__(self, repository: RagRepository | None = None) -> None:
        self._repo = repository or get_rag_repository()

    async def can_read_document(
        self,
        db: AsyncSession,
        *,
        access: AccessContext,
        document: RagDocument,
    ) -> bool:
        if access.is_admin:
            return True
        if str(document.user_id) == access.user_id:
            return True
        if document.project_id and await self.can_access_project(
            db, user_id=access.user_id, project_id=document.project_id
        ):
            return str(document.user_id) in await self._project_owner_ids(
                db, project_id=document.project_id
            )
        return False

    async def can_write_document(
        self,
        db: AsyncSession,
        *,
        access: AccessContext,
        document: RagDocument,
    ) -> bool:
        if access.is_admin:
            return True
        return str(document.user_id) == access.user_id

    async def can_access_project(
        self, db: AsyncSession, *, user_id: str, project_id: str
    ) -> bool:
        if project_id.startswith("classroom:"):
            grant_id = project_id.split(":", 1)[1]
            try:
                grant_uuid = uuid.UUID(grant_id)
            except ValueError:
                return False
            grant = (
                await db.execute(
                    select(ClassroomGrant).where(ClassroomGrant.id == grant_uuid)
                )
            ).scalar_one_or_none()
            if grant is None:
                return False
            return user_id in {str(grant.teacher_id), str(grant.student_id)}
        return False

    async def allowed_owner_ids_for_retrieval(
        self,
        db: AsyncSession,
        *,
        access: AccessContext,
        project_id: str | None,
    ) -> list[str]:
        if project_id:
            if not await self.can_access_project(db, user_id=access.user_id, project_id=project_id):
                raise PermissionError("Not authorized for this project")
            owners = await self._project_owner_ids(db, project_id=project_id)
            return owners
        return [access.user_id]

    async def _project_owner_ids(self, db: AsyncSession, *, project_id: str) -> list[str]:
        if project_id.startswith("classroom:"):
            grant_id = project_id.split(":", 1)[1]
            grant = (
                await db.execute(
                    select(ClassroomGrant).where(ClassroomGrant.id == uuid.UUID(grant_id))
                )
            ).scalar_one_or_none()
            if grant is None:
                return []
            return [str(grant.teacher_id)]
        return []


_policy: RagPolicyService | None = None


def get_rag_policy_service() -> RagPolicyService:
    global _policy
    if _policy is None:
        _policy = RagPolicyService()
    return _policy
