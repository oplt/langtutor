from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

from backend.app.modules.auth.oauth_state import (
    _memory_state,
    google_oauth_state_put,
    google_oauth_state_take,
)


def test_google_oauth_state_roundtrip_memory_fallback(monkeypatch) -> None:
    async def _run() -> None:
        _memory_state.clear()
        monkeypatch.setattr(
            "backend.app.modules.auth.oauth_state.redis_set_json",
            AsyncMock(return_value=False),
        )
        monkeypatch.setattr(
            "backend.app.modules.auth.oauth_state.redis_getdel",
            AsyncMock(return_value=None),
        )

        state = await google_oauth_state_put("signin")
        assert await google_oauth_state_take(state) == "signin"
        assert await google_oauth_state_take(state) is None

    asyncio.run(_run())
