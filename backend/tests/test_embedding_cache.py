from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from backend.app.modules.rag.application.embedding_cache import (
    get_cached_embedding,
    set_cached_embedding,
)


def test_embedding_cache_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    store: dict[str, list[float]] = {}

    async def _get(key: str):
        return store.get(key)

    async def _set(key: str, value, *, ttl_seconds: int) -> bool:
        store[key] = value
        return True

    monkeypatch.setattr(
        "backend.app.modules.rag.application.embedding_cache.redis_get_json",
        _get,
    )
    monkeypatch.setattr(
        "backend.app.modules.rag.application.embedding_cache.redis_set_json",
        _set,
    )

    async def _run() -> None:
        await set_cached_embedding("hallo", [0.1, 0.2])
        cached = await get_cached_embedding("hallo")
        assert cached == [0.1, 0.2]

    asyncio.run(_run())
