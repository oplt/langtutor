from __future__ import annotations

import uuid

from backend.app.modules.knowledge.search_cache import (
    Bm25Index,
    KnowledgeChunkSnapshot,
    KnowledgeSearchCache,
    _IndexedChunk,
    _deserialize_search_results,
    _serialize_search_results,
)


def _chunk(title: str, terms: dict[str, int]) -> _IndexedChunk:
    return _IndexedChunk(
        id=uuid.uuid4(),
        title=title,
        content=f"word: {title}",
        source="test",
        term_freqs=terms,
        token_count=max(sum(terms.values()), 1),
        metadata_json={},
    )


def test_bm25_index_returns_relevant_chunk() -> None:
    chunks = [_chunk("hallo", {"hallo": 1}), _chunk("dag", {"dag": 1})]
    index = Bm25Index(
        kb_name="test",
        revision="r1",
        doc_count=2,
        avg_doc_len=1.0,
        doc_freq={"hallo": 1, "dag": 1},
        chunks=chunks,
        inverted={"hallo": [0], "dag": [1]},
    )
    hits = index.search("hallo", top_k=3)
    assert len(hits) == 1
    assert hits[0][0].title == "hallo"


def test_search_cache_invalidate_clears_kb_entries() -> None:
    cache = KnowledgeSearchCache(ttl_seconds=600, max_entries=16)
    chunk = _chunk("hallo", {"hallo": 1})
    row = KnowledgeChunkSnapshot(
        id=chunk.id,
        title=chunk.title,
        content=chunk.content,
        source=chunk.source,
        metadata_json={},
    )
    cache._set_cached_search("kb", "rev", "hallo", 3, [(row, 1.0)])
    assert cache._get_cached_search("kb", "rev", "hallo", 3) is not None
    cache.invalidate_kb("kb")
    assert cache._get_cached_search("kb", "rev", "hallo", 3) is None


def test_search_results_serialize_roundtrip() -> None:
    chunk = KnowledgeChunkSnapshot(
        id=uuid.uuid4(),
        title="hallo",
        content="word: hallo",
        source="test",
        metadata_json={"rank": 1},
    )
    original = [(chunk, 1.23)]
    restored = _deserialize_search_results(_serialize_search_results(original))
    assert len(restored) == 1
    assert restored[0][0].title == "hallo"
    assert restored[0][1] == 1.23
