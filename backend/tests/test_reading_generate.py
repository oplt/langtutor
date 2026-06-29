from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.modules.reading.schemas import ReadingGenerateIn
from backend.app.modules.reading.source_fetcher import FetchedArticle


@pytest.fixture
def reading_client():
    from backend.app.main import create_app

    return TestClient(create_app(), raise_server_exceptions=False)


@pytest.mark.asyncio
async def test_reading_service_generate_with_mocks():
    from backend.app.modules.reading.application.service import ReadingService

    payload = ReadingGenerateIn(
        language="nl",
        level=2,
        maxFrequencyRank=1000,
        interestArea="daily_life",
        wordCount=300,
        sourceMode="generated",
        strictness="balanced",
    )
    article = FetchedArticle(
        title="Oefentekst",
        summary="Dit is een korte oefentekst over het dagelijks leven.",
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
        "replacements": [{"original": "dagelijks", "replacement": "elke dag", "reason": "simpler"}],
        "glossary": [{"word": "Nederland", "definition": "een land in Europa", "exampleSentence": ""}],
        "quiz": [
            {
                "question": "Waar gaat de tekst over?",
                "options": ["Het leven", "Sport", "Weer", "Muziek"],
                "answer": "Het leven",
            }
        ],
    }

    service = ReadingService()
    with (
        patch(
            "backend.app.modules.reading.application.service.fetch_source_material",
            new=AsyncMock(return_value=article),
        ),
        patch(
            "backend.app.modules.reading.application.service.adapt_reading_text",
            new=AsyncMock(return_value=llm_payload),
        ),
        patch(
            "backend.app.modules.reading.application.service.get_cached_reading_generate",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "backend.app.modules.reading.application.service.set_cached_reading_generate",
            new=AsyncMock(),
        ),
        patch("backend.app.modules.reading.application.service.settings") as mock_settings,
    ):
        mock_settings.AI_AGENT_ENABLED = True
        result = await service.generate(payload)

    assert result.adapted_text
    assert result.level == 2
    assert result.coverage.total_words >= 0
    assert len(result.replacements) == 1
    assert len(result.glossary) == 1
    assert len(result.quiz) == 1
    assert result.adaptation_mode == "llm"


def test_reading_generate_requires_auth(reading_client: TestClient):
    response = reading_client.post(
        "/api/reading/generate",
        json={
            "language": "nl",
            "level": 2,
            "maxFrequencyRank": 1000,
            "interestArea": "news",
            "wordCount": 300,
            "sourceMode": "generated",
            "strictness": "balanced",
        },
    )
    assert response.status_code in {401, 403}
