from __future__ import annotations

import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)

_GENERATE_CACHE_TTL_SECONDS = 300
_REDIS_PREFIX = "quiz:generate:"


def _cache_key(
    *,
    level: str,
    count: int,
    exercise_types: list[str],
    topic: str,
) -> str:
    types = ",".join(sorted(exercise_types))
    normalized_topic = " ".join(topic.strip().lower().split())
    digest = hashlib.sha256(f"{level}:{count}:{types}:{normalized_topic}".encode("utf-8")).hexdigest()[:20]
    return f"{_REDIS_PREFIX}{digest}"


async def get_cached_quiz_generate(
    *,
    level: str,
    count: int,
    exercise_types: list[str],
    topic: str,
) -> dict[str, Any] | None:
    from backend.app.core.redis_json import redis_get_json

    key = _cache_key(
        level=level,
        count=count,
        exercise_types=exercise_types,
        topic=topic,
    )
    cached = await redis_get_json(key)
    return cached if isinstance(cached, dict) else None


async def set_cached_quiz_generate(
    *,
    level: str,
    count: int,
    exercise_types: list[str],
    topic: str,
    payload: dict[str, Any],
) -> None:
    from backend.app.core.redis_json import redis_set_json

    key = _cache_key(
        level=level,
        count=count,
        exercise_types=exercise_types,
        topic=topic,
    )
    await redis_set_json(key, payload, ttl_seconds=_GENERATE_CACHE_TTL_SECONDS)
