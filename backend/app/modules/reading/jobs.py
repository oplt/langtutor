from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.app.modules.reading.schemas import ReadingGenerateIn, ReadingGenerateOut
    from backend.app.modules.reading.service import ReadingService

logger = logging.getLogger(__name__)

CancelCheck = Callable[[], Awaitable[bool] | bool]


@dataclass(frozen=True)
class ReadingGenerationJobRequest:
    payload: ReadingGenerateIn
    request_id: str = ""


class ReadingGenerationJobRunner:
    """Synchronous job boundary for reading generation.

    TODO(job-queue): enqueue `ReadingGenerationJobRequest` to a worker queue and
    expose `POST /api/reading/jobs` + `GET /api/reading/jobs/{id}` for polling.
    """

    def __init__(self, service: ReadingService) -> None:
        self._service = service

    async def run(
        self,
        payload: ReadingGenerateIn,
        *,
        cancel_check: CancelCheck | None = None,
    ) -> ReadingGenerateOut:
        logger.debug(
            "reading_generation_job_started level=%s interest=%s",
            payload.level,
            payload.interest_area,
        )
        return await self._service.generate(payload, cancel_check=cancel_check)
