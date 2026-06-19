from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_RAG_JOB_PROGRESS_TTL_SECONDS = 3600
_REDIS_PREFIX = "rag:job:"


def _cache_key(job_id: str) -> str:
    return f"{_REDIS_PREFIX}{job_id}"


async def set_rag_job_progress(
    job_id: str,
    *,
    status: str,
    progress_stage: str | None = None,
    error_message: str | None = None,
) -> None:
    from backend.app.core.redis_json import redis_set_json

    payload: dict[str, Any] = {
        "job_id": job_id,
        "status": status,
        "progress_stage": progress_stage,
        "error_message": error_message,
    }
    await redis_set_json(
        _cache_key(job_id),
        payload,
        ttl_seconds=_RAG_JOB_PROGRESS_TTL_SECONDS,
    )


async def get_rag_job_progress(job_id: str) -> dict[str, Any] | None:
    from backend.app.core.redis_json import redis_get_json

    cached = await redis_get_json(_cache_key(job_id))
    return cached if isinstance(cached, dict) else None
