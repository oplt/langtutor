"""Optional PostgreSQL full-text search for the Dutch knowledge base."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.modules.knowledge.models import KnowledgeChunk
from backend.app.modules.knowledge.search_cache import KnowledgeChunkSnapshot


async def fts_search_chunks(
    db: AsyncSession,
    *,
    kb_id: uuid.UUID,
    query: str,
    top_k: int,
) -> list[tuple[KnowledgeChunkSnapshot, float]]:
    if not query.strip():
        return []

    ts_query = func.plainto_tsquery("dutch", query)
    rank = func.ts_rank_cd(
        func.to_tsvector("dutch", KnowledgeChunk.content),
        ts_query,
    ).label("rank")

    stmt = (
        select(KnowledgeChunk, rank)
        .where(KnowledgeChunk.knowledge_base_id == kb_id)
        .where(func.to_tsvector("dutch", KnowledgeChunk.content).op("@@")(ts_query))
        .order_by(rank.desc())
        .limit(top_k)
    )
    rows = (await db.execute(stmt)).all()
    results: list[tuple[KnowledgeChunkSnapshot, float]] = []
    for chunk, score in rows:
        results.append(
            (
                KnowledgeChunkSnapshot(
                    id=chunk.id,
                    title=chunk.title,
                    content=chunk.content,
                    source=chunk.source,
                    metadata_json=chunk.metadata_json or {},
                ),
                float(score or 0.0),
            )
        )
    return results
