"""Reciprocal rank fusion for hybrid vector + lexical retrieval."""

from __future__ import annotations

from backend.app.modules.rag.domain.models import RetrievedChunk

_RRF_K = 60


def reciprocal_rank_fusion(
    *ranked_lists: list[RetrievedChunk],
    top_k: int,
) -> list[RetrievedChunk]:
    if not ranked_lists:
        return []
    if len(ranked_lists) == 1:
        return ranked_lists[0][:top_k]

    scores: dict[str, float] = {}
    by_id: dict[str, RetrievedChunk] = {}
    for ranked in ranked_lists:
        for rank, chunk in enumerate(ranked, start=1):
            scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + (1.0 / (_RRF_K + rank))
            by_id.setdefault(chunk.chunk_id, chunk)

    ordered_ids = sorted(scores.keys(), key=lambda chunk_id: scores[chunk_id], reverse=True)
    merged: list[RetrievedChunk] = []
    for chunk_id in ordered_ids[: max(1, top_k)]:
        base = by_id[chunk_id]
        merged.append(
            RetrievedChunk(
                chunk_id=base.chunk_id,
                document_id=base.document_id,
                content=base.content,
                score=float(scores[chunk_id]),
                metadata={**base.metadata, "rrf_score": scores[chunk_id]},
                filename=base.filename,
                chunk_index=base.chunk_index,
                page_number=base.page_number,
            )
        )
    return merged
