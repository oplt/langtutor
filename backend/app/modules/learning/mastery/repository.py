from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.base import CEFRLevel
from backend.app.modules.learning.mastery.models import LearningProgress
from backend.app.modules.learning.models import UserMasteryProgress


class MasteryRepository:
    async def get_or_create(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        level: CEFRLevel,
        factory,
    ) -> tuple[UserMasteryProgress, LearningProgress]:
        row = (
            await db.execute(
                select(UserMasteryProgress)
                .where(UserMasteryProgress.user_id == user_id)
                .where(UserMasteryProgress.level == level)
            )
        ).scalar_one_or_none()
        if row is None:
            progress = factory()
            row = UserMasteryProgress(
                user_id=user_id,
                level=level,
                progress_json=progress.model_dump(mode="json"),
                version=progress.version,
            )
            db.add(row)
            await db.flush()
            return row, progress
        progress = LearningProgress.model_validate(row.progress_json)
        return row, progress

    async def save(
        self,
        db: AsyncSession,
        row: UserMasteryProgress,
        progress: LearningProgress,
    ) -> None:
        progress.version += 1
        progress.updated_at = progress.updated_at
        row.progress_json = progress.model_dump(mode="json")
        row.version = progress.version
        await db.flush()
