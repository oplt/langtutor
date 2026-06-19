"""Lightweight reranking for retrieved document chunks."""

from __future__ import annotations

import re

from backend.app.core.config import settings
from backend.app.modules.rag.domain.models import RetrievedChunk

_TOKEN = re.compile(r"[a-zà-ü0-9]+", re.I)

_DUTCH_SUFFIXES = (
    "heden",
    "elijk",
    "lijk",
    "ing",
    "tion",
    "ment",
    "en",
    "er",
    "e",
)


def dutch_stem(token: str) -> str:
    lowered = token.lower()
    if len(lowered) <= 4:
        return lowered
    for suffix in _DUTCH_SUFFIXES:
        if lowered.endswith(suffix) and len(lowered) > len(suffix) + 2:
            return lowered[: -len(suffix)]
    return lowered


def _query_terms(query: str) -> set[str]:
    raw = {token.lower() for token in _TOKEN.findall(query) if len(token) >= 3}
    stemmed = {dutch_stem(token) for token in raw}
    return raw | stemmed


def filter_by_score_threshold(
    chunks: list[RetrievedChunk],
    *,
    threshold: float | None = None,
) -> list[RetrievedChunk]:
    floor = threshold if threshold is not None else settings.RAG_SCORE_THRESHOLD
    return [chunk for chunk in chunks if chunk.score >= floor]


def rerank_chunks(query: str, chunks: list[RetrievedChunk], top_k: int) -> list[RetrievedChunk]:
    if len(chunks) <= 1:
        return chunks[:top_k]

    terms = _query_terms(query)
    if not terms:
        return sorted(chunks, key=lambda item: item.score, reverse=True)[:top_k]

    def combined_score(chunk: RetrievedChunk) -> float:
        tokens = {dutch_stem(token) for token in _TOKEN.findall(chunk.content.lower()) if len(token) >= 3}
        overlap = len(terms & tokens)
        stem_overlap = sum(
            1
            for term in terms
            if any(token.startswith(term) or term.startswith(token) for token in tokens)
        )
        return chunk.score + overlap * 0.05 + stem_overlap * 0.02

    ranked = sorted(chunks, key=combined_score, reverse=True)
    return ranked[: max(1, top_k)]
