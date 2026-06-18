from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from backend.app.modules.users.models import User
from backend.app.db.session import get_db
from backend.app.modules.auth.dependencies import get_current_user
from backend.app.modules.extensions.visualize.service import get_visualize_service
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/extensions/visualize", tags=["extensions-visualize"])


@router.get("/progress")
async def progress_charts(
    level: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = get_visualize_service()
    return await service.build_progress_charts(db, user_id=user.id, level=level)
