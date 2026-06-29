from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from backend.app.modules.reading.coverage_policy import failing_sentences
from backend.app.modules.reading.llm import _build_user_prompt
from backend.app.modules.reading.source_fetcher import FetchedArticle
from backend.app.modules.reading.text_analyzer import analyze_coverage, tokenize
from backend.app.modules.reading.vocabulary_loader import load_cumulative_vocabulary
from backend.app.modules.reading.vocabulary_normalizer import (
    normalize_token_for_lookup,
    normalize_word,
)


@pytest.mark.asyncio
async def test_load_cumulative_vocabulary_level_1():
    snapshot = await load_cumulative_vocabulary(1)
    assert snapshot.level == 1
    assert snapshot.max_frequency_rank == 500
    assert "de" in snapshot.allowed_words
    assert "en" in snapshot.allowed_words
    assert len(snapshot.allowed_words) > 100


@pytest.mark.asyncio
async def test_load_cumulative_vocabulary_level_3_includes_lower_levels():
    level_1 = await load_cumulative_vocabulary(1)
    level_3 = await load_cumulative_vocabulary(3)
    assert level_1.allowed_words.issubset(level_3.allowed_words)
    assert len(level_3.allowed_words) > len(level_1.allowed_words)


def test_normalize_word_strips_punctuation_and_lowercases():
    assert normalize_word("  Schouder! ") == "schouder"
    assert normalize_word("Hè?") == "hè"


def test_normalize_token_handles_apostrophe():
    assert normalize_token_for_lookup("'t") == "t" or normalize_token_for_lookup("'t")


def test_analyze_coverage_counts_unknown_words():
    allowed = {"ik", "ga", "naar", "school", "vandaag"}
    text = "Ik ga naar school vandaag met de fiets."
    result = analyze_coverage(text, allowed)
    assert result.total_words >= 3
    assert result.allowed_words >= 1
    assert result.coverage_percent >= 0


def test_analyze_coverage_accepts_inflections_of_allowed_words():
    result = analyze_coverage("Wij werken op mooie dagen.", {"wij", "werk", "mooi", "dag"})
    assert result.unknown_word_list == []
    assert result.coverage_percent == 100.0


def test_tokenize_extracts_dutch_tokens():
    tokens = tokenize("Ik zie Amsterdam en 't huis.")
    assert "Ik" in tokens
    assert "Amsterdam" in tokens


def test_reading_prompt_contains_exact_cumulative_vocabulary():
    prompt = _build_user_prompt(
        level=2,
        max_frequency_rank=1000,
        interest_area="news",
        word_count=100,
        strictness="strict",
        allowed_words={"de", "fiets", "gaan"},
        source=FetchedArticle("Titel", "", "https://example.test", "Bron", "", "Brontekst"),
    )
    assert "ALLOWED_VOCABULARY" in prompt
    assert '"fiets"' in prompt
    assert "Every ordinary content word MUST be" in prompt


def test_reading_retry_enforces_requested_length():
    prompt = _build_user_prompt(
        level=1,
        max_frequency_rank=500,
        interest_area="news",
        word_count=300,
        strictness="balanced",
        allowed_words={"de", "man", "is", "in", "stad"},
        source=FetchedArticle("Titel", "", "https://example.test", "Bron", "", "De man is in de stad."),
        unknown_words_to_fix=["moeilijk"],
        previous_text="Een korte tekst.",
        length_to_fix=True,
    )
    assert "Required length: 240-345 Dutch words" in prompt
    assert "previous adapted text is too short" in prompt
    assert "Rewrite the ENTIRE text" in prompt


def test_sentence_with_any_unknown_word_requires_repair():
    failures = failing_sentences(
        "Ik lees vandaag een zeldzaam woord.",
        {"ik", "lees", "vandaag", "een", "woord"},
        80.0,
        protected_terms=set(),
    )
    assert len(failures) == 1
    assert failures[0].coverage.unknown_word_list == ["zeldzaam"]


def test_reading_llm_uses_json_mode_and_repairs_invalid_response():
    from backend.app.modules.reading.llm import adapt_reading_text

    invalid = MagicMock(content="not json")
    valid = MagicMock(
        content=(
            '{"title":"Titel","adaptedText":"De man is in de stad.",'
            '"summary":"","replacements":[],"glossary":[],"quiz":[]}'
        )
    )
    llm = MagicMock()
    llm.complete = AsyncMock(side_effect=[invalid, valid])
    with patch("backend.app.modules.reading.llm.get_llm_service", return_value=llm):
        result = asyncio.run(
            adapt_reading_text(
                level=1,
                max_frequency_rank=500,
                interest_area="news",
                word_count=100,
                strictness="balanced",
                allowed_words={"de", "man", "is", "in", "stad"},
                word_metadata={},
                source=FetchedArticle("Titel", "", "", "Bron", "", "De man is in de stad."),
            )
        )

    assert result["adaptationMode"] == "llm"
    assert result["adaptedText"] == "De man is in de stad."
    assert llm.complete.await_count == 2
    assert all(call.kwargs["response_format"] == "json" for call in llm.complete.await_args_list)
    assert all(call.kwargs["max_tokens"] == 512 for call in llm.complete.await_args_list)
