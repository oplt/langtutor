"""Lightweight reranking for retrieved document chunks (v1: score + lexical overlap)."""

from __future__ import annotations

import re

from backend.app.modules.rag.domain.models import RetrievedChunk

_TOKEN = re.compile(r"[a-z0-9]+", re.I)


def _query_terms(query: str) -> set[str]:
    return {token.lower() for token in _TOKEN.findall(query) if len(token) >= 3}


def rerank_chunks(query: str, chunks: list[RetrievedChunk], top_k: int) -> list[RetrievedChunk]:
    if len(chunks) <= 1:
        return chunks[:top_k]

    terms = _query_terms(query)
    if not terms:
        return sorted(chunks, key=lambda item: item.score, reverse=True)[:top_k]

    def combined_score(chunk: RetrievedChunk) -> float:
        text = chunk.content.lower()
        overlap = sum(1 for term in terms if term in text)
        return chunk.score + overlap * 0.04

    ranked = sorted(chunks, key=combined_score, reverse=True)
    return ranked[: max(1, top_k)]
