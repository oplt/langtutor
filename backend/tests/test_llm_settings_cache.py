from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from backend.app.modules.ai.schemas import LLMSettingsResponse
from backend.app.modules.ai.service import AISettingsService, invalidate_llm_settings_cache


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    invalidate_llm_settings_cache()
    yield
    invalidate_llm_settings_cache()


def test_get_settings_uses_ttl_cache() -> None:
    async def _run() -> None:
        repo = MagicMock()
        repo.get_settings_doc = AsyncMock(return_value=MagicMock(model_dump=lambda: {"ai": {}}))
        service = AISettingsService(repo=repo)

        first = await service.get_settings()
        second = await service.get_settings()

        assert isinstance(first, LLMSettingsResponse)
        assert first is second
        repo.get_settings_doc.assert_awaited_once()

    asyncio.run(_run())


def test_invalidate_clears_settings_cache() -> None:
    async def _run() -> None:
        repo = MagicMock()
        repo.get_settings_doc = AsyncMock(return_value=MagicMock(model_dump=lambda: {"ai": {}}))
        service = AISettingsService(repo=repo)

        await service.get_settings()
        invalidate_llm_settings_cache()
        await service.get_settings()

        assert repo.get_settings_doc.await_count == 2

    asyncio.run(_run())
