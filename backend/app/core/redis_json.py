from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


async def redis_get_json(key: str) -> Any | None:
    try:
        from backend.app.core.redis import get_redis

        raw = await get_redis().get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception:
        logger.debug("redis_json_get_failed key=%s", key, exc_info=True)
        return None


async def redis_set_json(key: str, value: Any, *, ttl_seconds: int) -> bool:
    try:
        from backend.app.core.redis import get_redis

        await get_redis().set(key, json.dumps(value), ex=max(1, ttl_seconds))
        return True
    except Exception:
        logger.debug("redis_json_set_failed key=%s", key, exc_info=True)
        return False


async def redis_delete(key: str) -> None:
    try:
        from backend.app.core.redis import get_redis

        await get_redis().delete(key)
    except Exception:
        logger.debug("redis_delete_failed key=%s", key, exc_info=True)


async def redis_getdel(key: str) -> Any | None:
    try:
        from backend.app.core.redis import get_redis

        raw = await get_redis().getdel(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception:
        logger.debug("redis_getdel_failed key=%s", key, exc_info=True)
        return None
