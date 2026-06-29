from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from backend.app.modules.reading.schemas import ReadingGenerateIn
from backend.app.modules.reading.source_fetcher import FetchedArticle
from backend.app.modules.translation.deepl_client import DeepLClient, DeepLTranslationResult
from backend.app.modules.translation.schemas import TranslationOut
from backend.app.modules.translation.service import TranslationService


def test_translation_disabled_returns_status_disabled():
    service = TranslationService(deepl_client=None)
    with patch("backend.app.modules.translation.service.settings") as mock_settings:
        mock_settings.DEEPL_ENABLED = False
        mock_settings.DEEPL_SOURCE_LANG = "NL"
        mock_settings.DEEPL_TARGET_LANG = "EN-US"
        mock_settings.DEEPL_MODEL_TYPE = ""
        translation, warnings = asyncio.run(
            service.translate_to_english(text="Hallo wereld.")
        )
    assert translation.status == "disabled"
    assert translation.text is None
    assert warnings == []


def test_missing_deepl_key_does_not_crash_reading_generation():
    from backend.app.modules.reading.service import ReadingService

    payload = ReadingGenerateIn(
        language="nl",
        level=2,
        maxFrequencyRank=1000,
        interestArea="daily_life",
        wordCount=300,
        sourceMode="generated",
        strictness="balanced",
        translationMode="full",
    )
    article = FetchedArticle(
        title="Oefentekst",
        summary="Korte samenvatting.",
        url="",
        publisher="LanguageApp",
        published_at="",
        content="Dit is een korte oefentekst over het dagelijks leven in Nederland.",
    )
    llm_payload = {
        "title": "Oefentekst",
        "adaptedText": "Ik lees een korte tekst over het leven in Nederland.",
        "summary": "Een eenvoudige tekst.",
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
            "backend.app.modules.reading.service.get_cached_reading_generate",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "backend.app.modules.reading.service.set_cached_reading_generate",
            new=AsyncMock(),
        ),
        patch("backend.app.modules.reading.service.settings") as mock_settings,
        patch("backend.app.modules.translation.service.settings") as translation_settings,
        patch("backend.app.modules.translation.service.build_deepl_client", return_value=None),
    ):
        mock_settings.AI_AGENT_ENABLED = True
        mock_settings.READING_COVERAGE_MAX_ATTEMPTS = 1
        translation_settings.DEEPL_ENABLED = True
        translation_settings.DEEPL_SOURCE_LANG = "NL"
        translation_settings.DEEPL_TARGET_LANG = "EN-US"
        translation_settings.DEEPL_MODEL_TYPE = ""
        result = asyncio.run(service.generate(payload))

    assert result.adapted_text
    assert result.translation is not None
    assert result.translation.status == "unavailable"
    assert any("temporarily unavailable" in warning.lower() for warning in result.warnings)


def test_successful_deepl_response_is_included_in_reading_response():
    from backend.app.modules.reading.service import ReadingService

    payload = ReadingGenerateIn(
        language="nl",
        level=2,
        maxFrequencyRank=1000,
        interestArea="daily_life",
        wordCount=300,
        sourceMode="generated",
        strictness="balanced",
        translationMode="full",
    )
    article = FetchedArticle(
        title="Oefentekst",
        summary="Korte samenvatting.",
        url="",
        publisher="LanguageApp",
        published_at="",
        content="Dit is een korte oefentekst.",
    )
    llm_payload = {
        "title": "Oefentekst",
        "adaptedText": "Ik lees een korte tekst.",
        "summary": "Een eenvoudige tekst.",
        "adaptationMode": "llm",
        "warnings": [],
        "replacements": [],
        "glossary": [],
        "quiz": [],
    }
    translation_service = TranslationService(MagicMock())
    translation_service.translate_to_english = AsyncMock(
        return_value=(
            TranslationOut(
                provider="deepl",
                language="EN-US",
                status="ok",
                text="I read a short text.",
            ),
            [],
        )
    )
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
            "backend.app.modules.reading.service.get_cached_reading_generate",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "backend.app.modules.reading.service.set_cached_reading_generate",
            new=AsyncMock(),
        ),
        patch(
            "backend.app.modules.reading.service.get_translation_service",
            return_value=translation_service,
        ),
        patch("backend.app.modules.reading.service.settings") as mock_settings,
    ):
        mock_settings.AI_AGENT_ENABLED = True
        mock_settings.READING_COVERAGE_MAX_ATTEMPTS = 1
        result = asyncio.run(ReadingService().generate(payload))

    assert result.translation is not None
    assert result.translation.status == "ok"
    assert result.translation.text == "I read a short text."
    assert result.translated_text == "I read a short text."
    translation_service.translate_to_english.assert_awaited_once()


def test_deepl_timeout_returns_dutch_text_with_translation_unavailable():
    service = TranslationService(
        DeepLClient(
            auth_key="test-key",
            api_base_url="https://api-free.deepl.com",
            timeout_seconds=1.0,
        )
    )
    request = httpx.Request("POST", "https://api-free.deepl.com/v2/translate")
    response = httpx.Response(504, request=request)
    with (
        patch("backend.app.modules.translation.service.settings") as mock_settings,
        patch(
            "backend.app.modules.translation.deepl_client.httpx.AsyncClient",
        ) as mock_client_cls,
        patch(
            "backend.app.modules.translation.cache.get_cached_translation",
            new=AsyncMock(return_value=None),
        ),
    ):
        mock_settings.DEEPL_ENABLED = True
        mock_settings.DEEPL_SOURCE_LANG = "NL"
        mock_settings.DEEPL_TARGET_LANG = "EN-US"
        mock_settings.DEEPL_MODEL_TYPE = ""
        client = mock_client_cls.return_value.__aenter__.return_value
        client.post = AsyncMock(
            side_effect=httpx.HTTPStatusError("timeout", request=request, response=response)
        )
        translation, warnings = asyncio.run(
            service.translate_to_english(text="Dit is Nederlands.")
        )

    assert translation.status == "unavailable"
    assert translation.text is None
    assert warnings


def test_deepl_called_only_after_final_accepted_dutch_text():
    from backend.app.modules.reading.service import ReadingService

    payload = ReadingGenerateIn(
        language="nl",
        level=2,
        maxFrequencyRank=1000,
        interestArea="daily_life",
        wordCount=300,
        sourceMode="generated",
        strictness="balanced",
        translationMode="full",
    )
    article = FetchedArticle(
        title="Oefentekst",
        summary="Korte samenvatting.",
        url="",
        publisher="LanguageApp",
        published_at="",
        content="Dit is een korte oefentekst.",
    )
    attempts = [
        {
            "title": "Oefentekst",
            "adaptedText": "Eerste poging met moeilijke woorden.",
            "summary": "Eerste",
            "adaptationMode": "llm",
            "warnings": [],
            "replacements": [],
            "glossary": [],
            "quiz": [],
        },
        {
            "title": "Oefentekst",
            "adaptedText": "De man is in de stad.",
            "summary": "Tweede",
            "adaptationMode": "llm",
            "warnings": [],
            "replacements": [],
            "glossary": [],
            "quiz": [],
        },
    ]
    translation_service = TranslationService(MagicMock())
    translation_service.translate_to_english = AsyncMock(
        return_value=(
            TranslationOut(
                provider="deepl",
                language="EN-US",
                status="ok",
                text="Second attempt with better words.",
            ),
            [],
        )
    )

    async def _adapt_side_effect(**kwargs):
        return attempts.pop(0)

    with (
        patch(
            "backend.app.modules.reading.service.fetch_source_material",
            new=AsyncMock(return_value=article),
        ),
        patch(
            "backend.app.modules.reading.service.adapt_reading_text",
            side_effect=_adapt_side_effect,
        ),
        patch(
            "backend.app.modules.reading.service.get_cached_reading_generate",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "backend.app.modules.reading.service.set_cached_reading_generate",
            new=AsyncMock(),
        ),
        patch(
            "backend.app.modules.reading.service.get_translation_service",
            return_value=translation_service,
        ),
        patch("backend.app.modules.reading.service.settings") as mock_settings,
    ):
        mock_settings.AI_AGENT_ENABLED = True
        mock_settings.READING_COVERAGE_MAX_ATTEMPTS = 2
        result = asyncio.run(ReadingService().generate(payload))

    assert result.adapted_text == "De man is in de stad."
    translation_service.translate_to_english.assert_awaited_once()
    assert (
        translation_service.translate_to_english.await_args.kwargs["text"]
        == "De man is in de stad."
    )


def test_translation_cache_prevents_duplicate_api_calls():
    cached = TranslationOut(
        provider="deepl",
        language="EN-US",
        status="ok",
        text="Cached translation.",
    ).model_dump(mode="json", by_alias=True)
    mock_client = MagicMock()
    mock_client.translate_text = AsyncMock(
        return_value=DeepLTranslationResult(text="Should not be called.")
    )
    service = TranslationService(mock_client)
    with (
        patch("backend.app.modules.translation.service.settings") as mock_settings,
        patch(
            "backend.app.modules.translation.service.get_cached_translation",
            new=AsyncMock(return_value=cached),
        ),
    ):
        mock_settings.DEEPL_ENABLED = True
        mock_settings.DEEPL_SOURCE_LANG = "NL"
        mock_settings.DEEPL_TARGET_LANG = "EN-US"
        mock_settings.DEEPL_MODEL_TYPE = ""
        translation, _warnings = asyncio.run(
            service.translate_to_english(text="De tekst.")
        )

    assert translation.status == "ok"
    assert translation.text == "Cached translation."
    mock_client.translate_text.assert_not_called()
