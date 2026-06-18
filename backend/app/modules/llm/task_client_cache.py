from __future__ import annotations

import time

from backend.app.core.config import settings
from backend.app.modules.llm.task_client import LLMTaskClient

_task_client_cache: dict[str, tuple[float, LLMTaskClient]] = {}


def invalidate_task_client_cache() -> None:
    _task_client_cache.clear()


def get_cached_task_client(task: str) -> LLMTaskClient | None:
    entry = _task_client_cache.get(task)
    if entry is None:
        return None
    expires_at, client = entry
    if time.monotonic() >= expires_at:
        _task_client_cache.pop(task, None)
        return None
    return client


def set_cached_task_client(task: str, client: LLMTaskClient) -> None:
    _task_client_cache[task] = (
        time.monotonic() + settings.LLM_TASK_CLIENT_CACHE_TTL_SECONDS,
        client,
    )
