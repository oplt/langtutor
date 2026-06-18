from __future__ import annotations

import time
import uuid

L3_READ_CACHE_TTL_SECONDS = 60
L3_MEMORY_BLOCK_KEY = "l3_memory_block"

_l3_read_cache: dict[str, tuple[str, float]] = {}


def get_l3_read_cache(user_id: uuid.UUID) -> str | None:
    entry = _l3_read_cache.get(str(user_id))
    if entry is None:
        return None
    text, expires_at = entry
    if time.monotonic() >= expires_at:
        _l3_read_cache.pop(str(user_id), None)
        return None
    return text


def set_l3_read_cache(user_id: uuid.UUID, text: str) -> None:
    _l3_read_cache[str(user_id)] = (
        text,
        time.monotonic() + L3_READ_CACHE_TTL_SECONDS,
    )


def invalidate_l3_read_cache(user_id: uuid.UUID) -> None:
    _l3_read_cache.pop(str(user_id), None)


def reset_l3_read_cache_for_tests() -> None:
    _l3_read_cache.clear()
