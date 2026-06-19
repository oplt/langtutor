from __future__ import annotations

import hashlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_FILE_CACHE_TTL_SECONDS = 86_400
_REDIS_PREFIX = "file:content:"

_memory: dict[str, tuple[float, str]] = {}


def read_text_cached(path: Path) -> str:
    """Read a file with an in-process mtime cache (safe for asyncio.to_thread callers)."""
    resolved = path.resolve()
    mtime = resolved.stat().st_mtime
    key = str(resolved)
    cached = _memory.get(key)
    if cached is not None and cached[0] == mtime:
        return cached[1]
    text = resolved.read_text(encoding="utf-8")
    _memory[key] = (mtime, text)
    return text


async def read_text_cached_redis(path: Path) -> str:
    """Read a file with Redis + in-process mtime cache for multi-worker coherence."""
    resolved = path.resolve()
    mtime = resolved.stat().st_mtime
    key = str(resolved)
    cached = _memory.get(key)
    if cached is not None and cached[0] == mtime:
        return cached[1]

    redis_key = _redis_key(resolved, mtime)
    try:
        from backend.app.core.redis_json import redis_get_json, redis_set_json

        remote = await redis_get_json(redis_key)
        if isinstance(remote, str):
            _memory[key] = (mtime, remote)
            return remote
    except Exception:
        logger.debug("file_cache_redis_get_failed path=%s", key, exc_info=True)

    text = resolved.read_text(encoding="utf-8")
    _memory[key] = (mtime, text)
    try:
        from backend.app.core.redis_json import redis_set_json

        await redis_set_json(redis_key, text, ttl_seconds=_FILE_CACHE_TTL_SECONDS)
    except Exception:
        logger.debug("file_cache_redis_set_failed path=%s", key, exc_info=True)
    return text


def reset_file_mtime_cache_for_tests() -> None:
    _memory.clear()


def _redis_key(path: Path, mtime: float) -> str:
    digest = hashlib.sha256(str(path.resolve()).encode("utf-8")).hexdigest()[:16]
    return f"{_REDIS_PREFIX}{digest}:{mtime:.6f}"
