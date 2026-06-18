from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from backend.app.core.config_validation import _validate_rag_embedding_dimension


def test_validate_rag_embedding_dimension_rejects_non_positive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "backend.app.core.config_validation.settings.RAG_EMBEDDING_DIMENSION",
        0,
    )
    with pytest.raises(ValueError, match="RAG_EMBEDDING_DIMENSION"):
        _validate_rag_embedding_dimension()


def test_validate_rag_embedding_dimension_warns_on_model_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(
        "backend.app.core.config_validation.settings.RAG_EMBEDDING_MODEL",
        "text-embedding-3-small",
    )
    monkeypatch.setattr(
        "backend.app.core.config_validation.settings.RAG_EMBEDDING_DIMENSION",
        768,
    )
    with caplog.at_level("WARNING"):
        _validate_rag_embedding_dimension()
    assert "runtime_config_embedding_dimension_mismatch" in caplog.text


def test_validate_runtime_config_pings_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        monkeypatch.setattr(
            "backend.app.core.config_validation.settings.RAG_ENABLED",
            False,
        )
        with (
            patch(
                "backend.app.core.health.check_redis",
                new_callable=AsyncMock,
                return_value=True,
            ) as redis_check,
            patch(
                "backend.app.modules.ai.service.AISettingsService",
            ) as settings_cls,
        ):
            settings_cls.return_value.get_settings = AsyncMock(return_value=type("S", (), {"profiles": []})())
            from backend.app.core.config_validation import validate_runtime_config

            await validate_runtime_config()
            redis_check.assert_awaited_once()

    asyncio.run(_run())
