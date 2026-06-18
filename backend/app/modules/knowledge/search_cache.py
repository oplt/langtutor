from __future__ import annotations

import hashlib
import heapq
import logging
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.modules.knowledge.bm25 import bm25_score, tokenize
from backend.app.modules.knowledge.models import KnowledgeBase, KnowledgeChunk

logger = logging.getLogger(__name__)

SEARCH_CACHE_TTL_SECONDS = 600
SEARCH_CACHE_MAX_ENTRIES = 1024
_REDIS_SEARCH_PREFIX = "kb:search:"


@dataclass(frozen=True)
class KnowledgeChunkSnapshot:
    """Lightweight chunk view used by cached search results."""

    id: uuid.UUID
    title: str
    content: str
    source: str
    metadata_json: dict[str, Any]


@dataclass(frozen=True)
class _IndexedChunk:
    id: uuid.UUID
    title: str
    content: str
    source: str
    term_freqs: dict[str, int]
    token_count: int
    metadata_json: dict[str, Any]


@dataclass
class Bm25Index:
    kb_name: str
    revision: str
    doc_count: int
    avg_doc_len: float
    doc_freq: dict[str, int]
    chunks: list[_IndexedChunk]
    inverted: dict[str, list[int]]

    def search(self, query: str, top_k: int) -> list[tuple[KnowledgeChunkSnapshot, float]]:
        terms = tokenize(query)
        if not terms or self.doc_count <= 0:
            return []

        candidate_indices: set[int] = set()
        for term in terms:
            for idx in self.inverted.get(term, ()):
                candidate_indices.add(idx)
        if not candidate_indices:
            return []

        limit = max(1, min(top_k, 20))
        best: list[tuple[float, int]] = []
        for idx in candidate_indices:
            chunk = self.chunks[idx]
            score = bm25_score(
                query_terms=terms,
                term_freqs=chunk.term_freqs,
                doc_len=chunk.token_count,
                avg_doc_len=self.avg_doc_len,
                doc_count=self.doc_count,
                doc_freq=self.doc_freq,
            )
            if score <= 0:
                continue
            if len(best) < limit:
                heapq.heappush(best, (score, idx))
            elif score > best[0][0]:
                heapq.heapreplace(best, (score, idx))

        ranked = sorted(best, key=lambda item: item[0], reverse=True)
        results: list[tuple[KnowledgeChunkSnapshot, float]] = []
        for score, idx in ranked:
            chunk = self.chunks[idx]
            results.append(
                (
                    KnowledgeChunkSnapshot(
                        id=chunk.id,
                        title=chunk.title,
                        content=chunk.content,
                        source=chunk.source,
                        metadata_json=chunk.metadata_json,
                    ),
                    float(score),
                )
            )
        return results


def _stats_revision(stats: dict[str, Any]) -> str:
    doc_count = int(stats.get("doc_count") or 0)
    updated_at = str(stats.get("updated_at") or "")
    return f"{doc_count}:{updated_at}"


def _snapshot_from_chunk(chunk: KnowledgeChunk) -> KnowledgeChunkSnapshot:
    return KnowledgeChunkSnapshot(
        id=chunk.id,
        title=chunk.title,
        content=chunk.content,
        source=chunk.source,
        metadata_json=dict(chunk.metadata_json or {}),
    )


def _indexed_from_chunk(chunk: KnowledgeChunk) -> _IndexedChunk:
    return _IndexedChunk(
        id=chunk.id,
        title=chunk.title,
        content=chunk.content,
        source=chunk.source,
        term_freqs=dict(chunk.term_freqs or {}),
        token_count=int(chunk.token_count or 0),
        metadata_json=dict(chunk.metadata_json or {}),
    )


def _redis_search_key(kb_name: str, revision: str, query: str, top_k: int) -> str:
    digest = hashlib.sha256(query.encode("utf-8")).hexdigest()[:16]
    return f"{_REDIS_SEARCH_PREFIX}{kb_name}:{revision}:{top_k}:{digest}"


def _serialize_search_results(
    results: list[tuple[KnowledgeChunkSnapshot, float]],
) -> list[dict[str, Any]]:
    return [
        {
            "id": str(chunk.id),
            "title": chunk.title,
            "content": chunk.content,
            "source": chunk.source,
            "metadata_json": chunk.metadata_json,
            "score": score,
        }
        for chunk, score in results
    ]


def _deserialize_search_results(
    payload: list[dict[str, Any]],
) -> list[tuple[KnowledgeChunkSnapshot, float]]:
    results: list[tuple[KnowledgeChunkSnapshot, float]] = []
    for item in payload:
        results.append(
            (
                KnowledgeChunkSnapshot(
                    id=uuid.UUID(str(item["id"])),
                    title=str(item.get("title") or ""),
                    content=str(item.get("content") or ""),
                    source=str(item.get("source") or ""),
                    metadata_json=dict(item.get("metadata_json") or {}),
                ),
                float(item.get("score") or 0.0),
            )
        )
    return results


async def _get_redis_search_cache(
    kb_name: str, revision: str, query: str, top_k: int
) -> list[tuple[KnowledgeChunkSnapshot, float]] | None:
    from backend.app.core.redis_json import redis_get_json

    key = _redis_search_key(kb_name, revision, query, top_k)
    cached = await redis_get_json(key)
    if not isinstance(cached, list):
        return None
    try:
        return _deserialize_search_results(cached)
    except (KeyError, TypeError, ValueError):
        logger.debug("kb_search_cache_corrupt key=%s", key)
        return None


async def _set_redis_search_cache(
    kb_name: str,
    revision: str,
    query: str,
    top_k: int,
    value: list[tuple[KnowledgeChunkSnapshot, float]],
) -> None:
    from backend.app.core.redis_json import redis_set_json

    key = _redis_search_key(kb_name, revision, query, top_k)
    await redis_set_json(
        key,
        _serialize_search_results(value),
        ttl_seconds=SEARCH_CACHE_TTL_SECONDS,
    )


async def _invalidate_kb_redis(kb_name: str) -> None:
    try:
        from backend.app.core.redis import get_redis

        redis = get_redis()
        pattern = f"{_REDIS_SEARCH_PREFIX}{kb_name}:*"
        cursor = 0
        while True:
            cursor, keys = await redis.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                await redis.delete(*keys)
            if cursor == 0:
                break
    except Exception:
        logger.debug("kb_search_redis_invalidate_failed kb=%s", kb_name, exc_info=True)


class KnowledgeSearchCache:
    """In-memory BM25 index + LRU search-result cache per knowledge base."""

    def __init__(
        self,
        *,
        ttl_seconds: float = SEARCH_CACHE_TTL_SECONDS,
        max_entries: int = SEARCH_CACHE_MAX_ENTRIES,
    ) -> None:
        self._ttl_seconds = ttl_seconds
        self._max_entries = max_entries
        self._indexes: dict[str, Bm25Index] = {}
        self._search_cache: OrderedDict[tuple[str, str, str, int], tuple[float, list[tuple[KnowledgeChunkSnapshot, float]]]] = (
            OrderedDict()
        )

    def invalidate_kb(self, kb_name: str) -> None:
        self._indexes.pop(kb_name, None)
        stale = [key for key in self._search_cache if key[0] == kb_name]
        for key in stale:
            self._search_cache.pop(key, None)

    async def invalidate_kb_async(self, kb_name: str) -> None:
        self.invalidate_kb(kb_name)
        await _invalidate_kb_redis(kb_name)

    async def load_index(self, db: AsyncSession, kb: KnowledgeBase) -> Bm25Index:
        stats = kb.stats_json or {}
        revision = _stats_revision(stats)
        cached = self._indexes.get(kb.name)
        if cached is not None and cached.revision == revision:
            return cached

        stale_keys = [key for key in self._search_cache if key[0] == kb.name]
        for key in stale_keys:
            self._search_cache.pop(key, None)

        rows = (
            await db.execute(
                select(KnowledgeChunk).where(KnowledgeChunk.knowledge_base_id == kb.id)
            )
        ).scalars().all()

        chunks = [_indexed_from_chunk(row) for row in rows]
        inverted: dict[str, list[int]] = {}
        for idx, chunk in enumerate(chunks):
            for term in chunk.term_freqs:
                inverted.setdefault(term, []).append(idx)

        index = Bm25Index(
            kb_name=kb.name,
            revision=revision,
            doc_count=int(stats.get("doc_count") or len(chunks)),
            avg_doc_len=float(stats.get("avg_doc_len") or 0.0),
            doc_freq=dict(stats.get("doc_freq") or {}),
            chunks=chunks,
            inverted=inverted,
        )
        self._indexes[kb.name] = index
        return index

    def _get_cached_search(
        self, kb_name: str, revision: str, query: str, top_k: int
    ) -> list[tuple[KnowledgeChunkSnapshot, float]] | None:
        key = (kb_name, revision, query, top_k)
        entry = self._search_cache.get(key)
        if entry is None:
            return None
        stored_at, value = entry
        if time.monotonic() - stored_at > self._ttl_seconds:
            self._search_cache.pop(key, None)
            return None
        self._search_cache.move_to_end(key)
        return value

    def _set_cached_search(
        self,
        kb_name: str,
        revision: str,
        query: str,
        top_k: int,
        value: list[tuple[KnowledgeChunkSnapshot, float]],
    ) -> None:
        key = (kb_name, revision, query, top_k)
        self._search_cache[key] = (time.monotonic(), value)
        self._search_cache.move_to_end(key)
        while len(self._search_cache) > self._max_entries:
            self._search_cache.popitem(last=False)

    async def search_indexed(
        self,
        db: AsyncSession,
        *,
        kb: KnowledgeBase,
        query: str,
        top_k: int,
    ) -> list[tuple[KnowledgeChunkSnapshot, float]]:
        normalized_query = " ".join(tokenize(query))
        if not normalized_query:
            return []

        index = await self.load_index(db, kb)
        cached = self._get_cached_search(kb.name, index.revision, normalized_query, top_k)
        if cached is not None:
            return cached

        redis_cached = await _get_redis_search_cache(
            kb.name, index.revision, normalized_query, top_k
        )
        if redis_cached is not None:
            self._set_cached_search(
                kb.name, index.revision, normalized_query, top_k, redis_cached
            )
            return redis_cached

        results = index.search(normalized_query, top_k)
        self._set_cached_search(kb.name, index.revision, normalized_query, top_k, results)
        await _set_redis_search_cache(
            kb.name, index.revision, normalized_query, top_k, results
        )
        return results


_cache: KnowledgeSearchCache | None = None


def get_knowledge_search_cache() -> KnowledgeSearchCache:
    global _cache
    if _cache is None:
        _cache = KnowledgeSearchCache()
    return _cache
