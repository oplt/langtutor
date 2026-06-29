from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.core.http_access_log import should_log_http_request
from backend.app.modules.llm.base import LLMChatRequest, LLMChatResponse, LLMProviderConfig
from backend.app.modules.llm.json_parse import LLMJsonParseError, extract_json_object
from backend.app.modules.llm.task_client import LLMTaskClient
from backend.app.modules.reading.schemas import ReadingGenerateIn
from backend.app.modules.reading.source_fetcher import FetchedArticle
from backend.app.modules.translation.schemas import TranslationOut


def test_should_log_http_request_excludes_metrics_and_health():
    assert should_log_http_request("/metrics") is False
    assert should_log_http_request("/health") is False
    assert should_log_http_request("/healthz") is False
    assert should_log_http_request("/ready") is False
    assert should_log_http_request("/api/reading/generate") is True


def test_metrics_not_access_logged(caplog: pytest.LogCaptureFixture):
    from backend.app.main import create_app

    caplog.set_level(logging.INFO, logger="backend")
    client = TestClient(create_app(), raise_server_exceptions=False)
    response = client.get("/metrics")
    assert response.status_code == 200
    assert not any(record.message == "http_request" for record in caplog.records)


def test_health_not_access_logged(caplog: pytest.LogCaptureFixture):
    from backend.app.main import create_app

    caplog.set_level(logging.INFO, logger="backend")
    client = TestClient(create_app(), raise_server_exceptions=False)
    response = client.get("/health")
    assert response.status_code == 200
    assert not any(record.message == "http_request" for record in caplog.records)


def test_extract_json_object_from_markdown_fence():
    payload = extract_json_object('Intro\n```json\n{"translatedText":"Hello"}\n```\nThanks')
    assert payload["translatedText"] == "Hello"


def test_extract_json_object_with_leading_and_trailing_text():
    payload = extract_json_object('Sure! {"translatedText":"Hallo"} is the answer.')
    assert payload["translatedText"] == "Hallo"


def test_extract_json_object_uses_first_valid_object():
    payload = extract_json_object('{"ignored":1} trailing {"translatedText":"Second"}')
    assert payload["ignored"] == 1


def test_extract_json_object_raises_for_invalid_payload():
    with pytest.raises(LLMJsonParseError):
        extract_json_object("not json at all")


def test_translate_adapted_text_repairs_invalid_json():
    asyncio.run(_test_translate_adapted_text_repairs_invalid_json())


async def _test_translate_adapted_text_repairs_invalid_json():
    from backend.app.modules.reading.llm import translate_adapted_text

    bad = MagicMock(content="Here you go: definitely not json")
    good = MagicMock(content='{"translatedText":"Good morning"}')

    with patch(
        "backend.app.modules.reading.llm.get_llm_service",
    ) as mock_service:
        llm = mock_service.return_value
        llm.complete = AsyncMock(side_effect=[bad, good])
        translated, sentences = await translate_adapted_text(
            text="Goedemorgen.",
            mode="full",
        )

    assert translated == "Good morning"
    assert sentences == []
    assert llm.complete.await_count == 2


def test_reading_generation_below_target_returns_best_fallback_with_warning():
    asyncio.run(_test_reading_generation_below_target_returns_best_fallback_with_warning())


async def _test_reading_generation_below_target_returns_best_fallback_with_warning():
    from backend.app.modules.reading.service import ReadingService

    payload = ReadingGenerateIn(
        language="nl",
        level=1,
        maxFrequencyRank=500,
        interestArea="daily_life",
        wordCount=300,
        sourceMode="generated",
        strictness="balanced",
    )
    article = FetchedArticle(
        title="Oefentekst",
        summary="Dit is een korte oefentekst.",
        url="",
        publisher="LanguageApp",
        published_at="",
        content="Dit is een korte oefentekst met zeer moeilijke woorden zoals quantum en astrofysica.",
    )
    llm_payload = {
        "title": "Oefentekst",
        "adaptedText": "Dit is een korte tekst met quantum en astrofysica.",
        "summary": "Een tekst.",
        "adaptationMode": "llm",
        "warnings": [],
        "replacements": [],
        "glossary": [],
        "quiz": [],
    }

    service = ReadingService()
    with (
        patch(
            "backend.app.modules.reading.service.fetch_source_material",
            new=AsyncMock(return_value=article),
        ),
        patch(
            "backend.app.modules.reading.service.adapt_reading_text",
            new=AsyncMock(return_value=llm_payload),
        ),
        patch(
            "backend.app.modules.reading.service.get_translation_service",
            return_value=MagicMock(
                translate_to_english=AsyncMock(
                    return_value=(
                        TranslationOut(
                            provider="deepl",
                            language="EN-US",
                            status="ok",
                            text="A short text.",
                        ),
                        [],
                    )
                )
            ),
        ),
        patch(
            "backend.app.modules.reading.service.get_cached_reading_generate",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "backend.app.modules.reading.service.set_cached_reading_generate",
            new=AsyncMock(),
        ),
        patch("backend.app.modules.reading.service.settings") as mock_settings,
    ):
        mock_settings.AI_AGENT_ENABLED = True
        mock_settings.READING_COVERAGE_MAX_ATTEMPTS = 1
        result = await service.generate(payload)

    assert result.adapted_text
    assert result.warning is not None
    assert result.coverage.coverage_percent < result.target_coverage_percent


def test_llm_slow_request_logged_once(caplog: pytest.LogCaptureFixture):
    asyncio.run(_test_llm_slow_request_logged_once(caplog))


async def _test_llm_slow_request_logged_once(caplog: pytest.LogCaptureFixture):
    caplog.set_level(logging.DEBUG)

    class SlowLLMClient:
        async def chat(self, request: LLMChatRequest) -> LLMChatResponse:
            await asyncio.sleep(0)
            return LLMChatResponse(
                provider="ollama",
                model="test-model",
                content="ok",
                raw={},
            )

        async def stream_chat(self, request: LLMChatRequest):
            yield "ok"

        async def health_check(self):
            return MagicMock(ok=True)

        async def list_models(self):
            return []

    config = LLMProviderConfig(provider="ollama", model="test-model", timeout_seconds=60.0)
    client = LLMTaskClient(task="reading_generation", client=SlowLLMClient(), config=config)

    with (
        patch("backend.app.modules.llm.task_client.time.perf_counter", side_effect=[0.0, 4.0]),
        patch(
            "backend.app.modules.llm.task_client.settings.SLOW_EXTERNAL_CALL_MS",
            3000,
        ),
        patch(
            "backend.app.modules.llm.http.settings.SLOW_EXTERNAL_CALL_MS",
            3000,
        ),
    ):
        await client.chat(LLMChatRequest(messages=[]))

    warnings = [record for record in caplog.records if record.levelno >= logging.WARNING]
    assert sum(record.message == "llm_request_slow" for record in warnings) == 1
    assert not any(record.message == "external_request_slow" for record in warnings)


def test_vocabulary_loader_caches_repeated_level_loads():
    asyncio.run(_test_vocabulary_loader_caches_repeated_level_loads())


async def _test_vocabulary_loader_caches_repeated_level_loads():
    from backend.app.modules.reading import vocabulary_loader as vocabulary_module

    vocabulary_module._load_level_files_cached.cache_clear()
    read_calls = 0
    original_read_text = Path.read_text

    def counting_read_text(self: Path, *args, **kwargs):
        nonlocal read_calls
        read_calls += 1
        return original_read_text(self, *args, **kwargs)

    with patch.object(Path, "read_text", counting_read_text):
        await vocabulary_module.load_cumulative_vocabulary(1)
        first_reads = read_calls
        await vocabulary_module.load_cumulative_vocabulary(1)
        second_reads = read_calls

    assert first_reads > 0
    assert second_reads == first_reads
