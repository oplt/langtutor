from __future__ import annotations

import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)

_DICT_CACHE_TTL_SECONDS = 3600
_REDIS_PREFIX = "dict:lemma:"


def _cache_key(lemma: str) -> str:
    normalized = lemma.strip().lower()
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return f"{_REDIS_PREFIX}{digest}"


async def get_dict_lookup(lemma: str) -> dict[str, Any] | None:
    from backend.app.core.redis_json import redis_get_json

    cached = await redis_get_json(_cache_key(lemma))
    if not isinstance(cached, dict):
        return None
    if "content" not in cached:
        return None
    return cached


async def set_dict_lookup(lemma: str, *, content: str, metadata: dict[str, Any]) -> None:
    from backend.app.core.redis_json import redis_set_json

    await redis_set_json(
        _cache_key(lemma),
        {"content": content, "metadata": metadata},
        ttl_seconds=_DICT_CACHE_TTL_SECONDS,
    )


async def invalidate_dict_lookups() -> None:
    try:
        from backend.app.core.redis import get_redis

        redis = get_redis()
        pattern = f"{_REDIS_PREFIX}*"
        cursor = 0
        while True:
            cursor, keys = await redis.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                await redis.delete(*keys)
            if cursor == 0:
                break
    except Exception:
        logger.debug("dict_lookup_cache_invalidate_failed", exc_info=True)
