from __future__ import annotations

import logging
import time
from typing import Any
from uuid import UUID

from backend.app.core.config import settings
from backend.app.core.redis_json import redis_delete, redis_get_json, redis_set_json

logger = logging.getLogger(__name__)

_LEVELS_CACHE_KEY = "learning:levels:v1"
_levels_memory: tuple[float, dict[str, Any]] | None = None


def _progress_cache_key(user_id: UUID) -> str:
    return f"learning:progress:{user_id}"


async def get_cached_levels() -> dict[str, Any] | None:
    global _levels_memory

    now = time.monotonic()
    if _levels_memory is not None and now < _levels_memory[0]:
        return _levels_memory[1]

    cached = await redis_get_json(_LEVELS_CACHE_KEY)
    if cached is not None:
        _levels_memory = (now + settings.LEARNING_LEVELS_CACHE_TTL_SECONDS, cached)
        return cached
    return None


async def set_cached_levels(payload: dict[str, Any]) -> None:
    global _levels_memory

    expires_at = time.monotonic() + settings.LEARNING_LEVELS_CACHE_TTL_SECONDS
    _levels_memory = (expires_at, payload)
    await redis_set_json(
        _LEVELS_CACHE_KEY,
        payload,
        ttl_seconds=settings.LEARNING_LEVELS_CACHE_TTL_SECONDS,
    )


async def invalidate_levels_cache() -> None:
    global _levels_memory

    _levels_memory = None
    await redis_delete(_LEVELS_CACHE_KEY)


async def get_cached_progress_summary(user_id: UUID) -> dict[str, Any] | None:
    return await redis_get_json(_progress_cache_key(user_id))


async def set_cached_progress_summary(user_id: UUID, payload: dict[str, Any]) -> None:
    await redis_set_json(
        _progress_cache_key(user_id),
        payload,
        ttl_seconds=settings.LEARNING_PROGRESS_CACHE_TTL_SECONDS,
    )


async def invalidate_progress_summary(user_id: UUID) -> None:
    await redis_delete(_progress_cache_key(user_id))
