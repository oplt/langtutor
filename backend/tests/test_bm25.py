from __future__ import annotations

from backend.app.modules.knowledge.bm25 import bm25_score, term_frequencies, tokenize


def test_tokenize_lowercases_words() -> None:
    assert tokenize("Hallo Wereld") == ["hallo", "wereld"]


def test_bm25_scores_matching_term_higher() -> None:
    doc_freq = {"hallo": 1, "dag": 1}
    high = bm25_score(
        query_terms=["hallo"],
        term_freqs={"hallo": 2, "wereld": 1},
        doc_len=3,
        avg_doc_len=3.0,
        doc_count=2,
        doc_freq=doc_freq,
    )
    low = bm25_score(
        query_terms=["hallo"],
        term_freqs={"dag": 1},
        doc_len=1,
        avg_doc_len=3.0,
        doc_count=2,
        doc_freq=doc_freq,
    )
    assert high > low


def test_term_frequencies_counts_tokens() -> None:
    freqs, count = term_frequencies("de de kat")
    assert count == 3
    assert freqs["de"] == 2
    assert freqs["kat"] == 1
