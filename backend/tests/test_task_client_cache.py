from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

from backend.app.modules.llm.service import create_task_client
from backend.app.modules.llm.task_client_cache import (
    get_cached_task_client,
    invalidate_task_client_cache,
    set_cached_task_client,
)


def test_task_client_cache_reuses_client() -> None:
    async def _run() -> None:
        invalidate_task_client_cache()
        client = MagicMock()
        set_cached_task_client("tutor_chat", client)
        assert get_cached_task_client("tutor_chat") is client

    asyncio.run(_run())


def test_create_task_client_uses_cache(monkeypatch) -> None:
    async def _run() -> None:
        invalidate_task_client_cache()
        cached = MagicMock()
        set_cached_task_client("tutor_chat", cached)

        create_mock = AsyncMock()
        monkeypatch.setattr("backend.app.modules.llm.service.create_llm_client", create_mock)

        resolved = await create_task_client("tutor_chat")
        assert resolved is cached
        create_mock.assert_not_called()

    asyncio.run(_run())


def test_task_client_cache_expires(monkeypatch) -> None:
    invalidate_task_client_cache()
    client = MagicMock()
    now = {"t": 1000.0}
    monkeypatch.setattr(time, "monotonic", lambda: now["t"])
    set_cached_task_client("tutor_chat", client)
    now["t"] += 10_000
    assert get_cached_task_client("tutor_chat") is None
