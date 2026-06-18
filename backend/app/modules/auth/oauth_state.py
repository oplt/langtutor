from __future__ import annotations

import logging
import secrets
import time
from typing import Optional

from backend.app.core.redis_json import redis_getdel, redis_set_json

logger = logging.getLogger(__name__)

GOOGLE_STATE_TTL_SECONDS = 600
_STATE_PREFIX = "oauth:google:state:"
_memory_state: dict[str, tuple[float, str]] = {}


def _purge_stale_memory() -> None:
    now = time.time()
    stale = [key for key, (expires_at, _mode) in _memory_state.items() if expires_at <= now]
    for key in stale:
        _memory_state.pop(key, None)


async def google_oauth_state_put(mode: str) -> str:
    state = secrets.token_urlsafe(24)
    payload = {"mode": mode}
    stored = await redis_set_json(
        f"{_STATE_PREFIX}{state}",
        payload,
        ttl_seconds=GOOGLE_STATE_TTL_SECONDS,
    )
    if not stored:
        _purge_stale_memory()
        _memory_state[state] = (time.time() + GOOGLE_STATE_TTL_SECONDS, mode)
    return state


async def google_oauth_state_take(state: str) -> Optional[str]:
    key = f"{_STATE_PREFIX}{state}"
    payload = await redis_getdel(key)
    if isinstance(payload, dict):
        mode = str(payload.get("mode") or "")
        return mode or None

    _purge_stale_memory()
    found = _memory_state.pop(state, None)
    if not found:
        return None
    expires_at, mode = found
    if expires_at <= time.time():
        return None
    return mode
