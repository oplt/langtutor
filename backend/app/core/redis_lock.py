from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_LOCK_PREFIX = "lock:"
_memory_locks: set[str] = set()


async def try_acquire_job_lock(lock_key: str, *, ttl_seconds: int) -> bool:
    """Cross-worker deduplication for background work; falls back to in-process locks."""
    full_key = f"{_LOCK_PREFIX}{lock_key}"
    try:
        from backend.app.core.redis import get_redis

        acquired = await get_redis().set(full_key, "1", nx=True, ex=max(1, ttl_seconds))
        return bool(acquired)
    except Exception:
        logger.debug("redis_job_lock_unavailable key=%s", lock_key, exc_info=True)
        if lock_key in _memory_locks:
            return False
        _memory_locks.add(lock_key)
        return True


async def release_job_lock(lock_key: str) -> None:
    full_key = f"{_LOCK_PREFIX}{lock_key}"
    try:
        from backend.app.core.redis import get_redis

        await get_redis().delete(full_key)
    except Exception:
        logger.debug("redis_job_lock_release_failed key=%s", lock_key, exc_info=True)
    _memory_locks.discard(lock_key)


def reset_job_locks_for_tests() -> None:
    _memory_locks.clear()
