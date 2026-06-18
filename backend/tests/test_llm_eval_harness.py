"""Regression-style eval fixtures for grounding and quiz quality (no live LLM calls)."""

from __future__ import annotations

import uuid

from backend.app.modules.knowledge.cefr_filters import chunk_matches_cefr
from backend.app.modules.knowledge.search_cache import Bm25Index, _IndexedChunk


def _chunk(title: str, terms: dict[str, int]) -> _IndexedChunk:
    return _IndexedChunk(
        id=uuid.uuid4(),
        title=title,
        content=f"lemma: {title}",
        source="eval",
        term_freqs=terms,
        token_count=max(sum(terms.values()), 1),
        metadata_json={},
    )


def test_grounding_bm25_prefers_exact_lemma() -> None:
    chunks = [
        _chunk("hallo", {"hallo": 2, "groet": 1}),
        _chunk("dag", {"dag": 2, "groet": 1}),
    ]
    index = Bm25Index(
        kb_name="eval",
        revision="r1",
        doc_count=2,
        avg_doc_len=3.0,
        doc_freq={"hallo": 1, "dag": 1, "groet": 2},
        chunks=chunks,
        inverted={"hallo": [0], "dag": [1], "groet": [0, 1]},
    )
    hits = index.search("hallo", top_k=1)
    assert hits
    assert hits[0][0].title == "hallo"
    assert hits[0][1] > 0.0


def test_grounding_cefr_filter_excludes_out_of_band_rank() -> None:
    metadata = {"rank": 5000}
    assert chunk_matches_cefr(metadata, cefr_level="A1") is False
    assert chunk_matches_cefr({"rank": 50}, cefr_level="A1") is True


def test_quiz_exact_match_is_deterministic() -> None:
    expected = "ik ben"
    actual = "Ik ben."
    normalized_expected = expected.strip().lower()
    normalized_actual = actual.strip().lower().strip(".")
    assert normalized_actual == normalized_expected
