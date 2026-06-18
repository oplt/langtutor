from __future__ import annotations

import logging
from typing import Optional

from redis.asyncio import Redis

from backend.app.core.config import settings

logger = logging.getLogger("backend")

_redis_client: Optional[Redis] = None


def get_redis() -> Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        logger.info("Redis client initialized", extra={"redis_url": settings.REDIS_URL})
    return _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        try:
            await _redis_client.close()
        except Exception:
            logger.warning("Failed to close Redis client", exc_info=True)
        finally:
            _redis_client = None
