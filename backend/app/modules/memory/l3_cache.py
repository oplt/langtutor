from __future__ import annotations

import logging
import uuid

logger = logging.getLogger(__name__)

L3_READ_CACHE_TTL_SECONDS = 60
L3_CAPABILITY_CACHE_TTL_SECONDS = 90
L3_MEMORY_BLOCK_KEY = "l3_memory_block"
_REDIS_CAPABILITY_PREFIX = "memory:l3:"
_REDIS_FULL_READ_PREFIX = "memory:l3:full:"


async def get_l3_read_cache(user_id: uuid.UUID) -> str | None:
    from backend.app.core.redis_json import redis_get_json

    cached = await redis_get_json(_full_read_cache_key(user_id))
    if isinstance(cached, str):
        return cached
    return None


async def set_l3_read_cache(user_id: uuid.UUID, text: str) -> None:
    from backend.app.core.redis_json import redis_set_json

    await redis_set_json(
        _full_read_cache_key(user_id),
        text,
        ttl_seconds=L3_READ_CACHE_TTL_SECONDS,
    )


def invalidate_l3_read_cache(user_id: uuid.UUID) -> None:
    """Sync no-op kept for callers/tests; use ``invalidate_l3_read_cache_async`` in async code."""
    _ = user_id


async def get_l3_capability_cache(user_id: uuid.UUID, capability: str) -> str | None:
    from backend.app.core.redis_json import redis_get_json

    key = _capability_cache_key(user_id, capability)
    cached = await redis_get_json(key)
    if isinstance(cached, str):
        return cached
    return None


async def set_l3_capability_cache(user_id: uuid.UUID, capability: str, text: str) -> None:
    from backend.app.core.redis_json import redis_set_json

    await redis_set_json(
        _capability_cache_key(user_id, capability),
        text,
        ttl_seconds=L3_CAPABILITY_CACHE_TTL_SECONDS,
    )


async def invalidate_l3_read_cache_async(user_id: uuid.UUID) -> None:
    from backend.app.core.redis_json import redis_delete

    await redis_delete(_full_read_cache_key(user_id))
    try:
        from backend.app.core.redis import get_redis

        redis = get_redis()
        pattern = f"{_REDIS_CAPABILITY_PREFIX}{user_id}:*"
        cursor = 0
        while True:
            cursor, keys = await redis.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                await redis.delete(*keys)
            if cursor == 0:
                break
    except Exception:
        logger.debug("l3_capability_cache_invalidate_failed user_id=%s", user_id, exc_info=True)


def reset_l3_read_cache_for_tests() -> None:
    """Test helper — Redis-backed cache resets via monkeypatch in unit tests."""
    return None


def _full_read_cache_key(user_id: uuid.UUID) -> str:
    return f"{_REDIS_FULL_READ_PREFIX}{user_id}"


def _capability_cache_key(user_id: uuid.UUID, capability: str) -> str:
    slug = (capability or "all").strip().lower() or "all"
    return f"{_REDIS_CAPABILITY_PREFIX}{user_id}:{slug}"
