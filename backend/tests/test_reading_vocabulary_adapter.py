from __future__ import annotations

import pytest

from backend.app.modules.reading.vocabulary_adapter import adapt_text_with_rules


@pytest.mark.asyncio
async def test_rule_adapter_simplifies_and_tracks_replacements():
    allowed = {"ik", "ga", "naar", "school", "vandaag", "lopen", "kind", "leren"}
    metadata = {"school": {"translation": "school", "grammatical_structure": "noun"}}
    source = (
        "Ik ga vandaag naar school met mijn kind. "
        "We leren samen en wandelen door de stad."
    )
    result = adapt_text_with_rules(
        source_text=source,
        allowed_words=allowed,
        word_metadata=metadata,
        level=1,
        word_count=80,
        strictness="strict",
        title="Test",
    )
    assert result.adapted_text
    assert result.adapted_text != source or result.glossary
    assert isinstance(result.replacements, list)
    assert isinstance(result.glossary, list)
