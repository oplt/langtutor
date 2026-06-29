from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.exceptions import AppError
from backend.app.db.session import get_db
from backend.app.deps import reading_job_runner_dep, reading_service_dep
from backend.app.modules.auth.dependencies import get_current_user
from backend.app.modules.reading.jobs import ReadingGenerationJobRunner
from backend.app.modules.reading.schemas import ReadingGenerateIn, ReadingGenerateOut, ReadingSaveIn, ReadingSaveOut
from backend.app.modules.reading.service import ReadingService
from backend.app.modules.users.models import User

router = APIRouter(prefix="/api/reading", tags=["reading"])
logger = logging.getLogger(__name__)


@router.post("/generate", response_model=ReadingGenerateOut)
async def generate_reading(
    payload: ReadingGenerateIn,
    request: Request,
    user: User = Depends(get_current_user),
    runner: ReadingGenerationJobRunner = Depends(reading_job_runner_dep),
):
    # Auth dependency is intentionally kept so this LLM/source-fetching endpoint
    # can be protected by per-user rate limits/quotas at middleware level.
    _ = user
    try:
        return await asyncio.wait_for(
            runner.run(
                payload,
                cancel_check=request.is_disconnected,
            ),
            timeout=float(settings.READING_GENERATE_TIMEOUT_SECONDS),
        )
    except asyncio.TimeoutError as exc:
        logger.warning(
            "reading_generation_timeout level=%s timeout_seconds=%s",
            payload.level,
            settings.READING_GENERATE_TIMEOUT_SECONDS,
        )
        raise AppError(
            code="reading_generation_timeout",
            message="Reading generation timed out. Try a shorter text or retry shortly.",
            status_code=504,
            details={"timeoutSeconds": settings.READING_GENERATE_TIMEOUT_SECONDS},
        ) from exc


@router.post("/save", response_model=ReadingSaveOut)
async def save_reading(
    payload: ReadingSaveIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: ReadingService = Depends(reading_service_dep),
):
    return await service.save(db, user_id=user.id, payload=payload.reading)
