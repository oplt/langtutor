from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import BASE_DIR, settings
from backend.app.modules.knowledge.bm25 import term_frequencies
from backend.app.modules.knowledge.models import KnowledgeBase, KnowledgeChunk
from backend.app.modules.knowledge.search_cache import (
    KnowledgeChunkSnapshot,
    get_knowledge_search_cache,
)

DEFAULT_KB_NAME = "dutch-core"
_INGEST_BATCH_SIZE = 500
_MAX_CHUNK_TITLE_LEN = 200
_MAX_WORD_TITLE_LEN = 80
DEFAULT_SOURCES = sorted((BASE_DIR.parent / "files" / "levels").glob("*.json"))


def _normalize_chunk_title(title: str) -> str | None:
    cleaned = title.strip()
    if not cleaned:
        return None
    if len(cleaned) > _MAX_WORD_TITLE_LEN:
        return None
    return cleaned[:_MAX_CHUNK_TITLE_LEN]


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _word_entry_to_text(entry: dict[str, Any]) -> str:
    word = str(entry.get("word") or "").strip()
    rank = entry.get("rank")
    translation = str(entry.get("translation") or "").strip()
    grammar = str(entry.get("grammatical_structure") or "").strip()
    example = str(entry.get("example") or "").strip()
    return (
        f"word: {word}\n"
        f"rank: {rank}\n"
        f"pos: {grammar}\n"
        f"translation: {translation}\n"
        f"example: {example}\n"
    ).strip()


def _load_file_chunks(path: Path) -> list[tuple[str, str, dict[str, Any]]]:
    """Return (title, content, metadata) chunks."""
    suffix = path.suffix.lower()
    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        entries = data if isinstance(data, list) else data.get("words", [])
        chunks = []
        for entry in entries:
            title = _normalize_chunk_title(str(entry.get("word") or ""))
            if title is None:
                continue
            content = _word_entry_to_text(entry)
            meta = {
                "rank": entry.get("rank"),
                "pos": entry.get("grammatical_structure"),
                "frequency": entry.get("frequency"),
            }
            if title and content:
                chunks.append((title, content, meta))
        return chunks

    # Generic fallback: split by blank lines.
    text = path.read_text(encoding="utf-8")
    parts = [part.strip() for part in text.split("\n\n") if part.strip()]
    title = path.name[:_MAX_CHUNK_TITLE_LEN]
    return [(title, part, {}) for part in parts]


@dataclass
class SearchHit:
    chunk: KnowledgeChunk | KnowledgeChunkSnapshot
    score: float


class KnowledgeService:
    async def ensure_default_kb(self, db: AsyncSession) -> KnowledgeBase:
        kb = (
            await db.execute(select(KnowledgeBase).where(KnowledgeBase.name == DEFAULT_KB_NAME))
        ).scalar_one_or_none()
        if kb is None:
            kb = KnowledgeBase(name=DEFAULT_KB_NAME, description="Dutch corpus + references")
            db.add(kb)
            await db.flush()
        return kb

    async def warmup_default_kb(self, db: AsyncSession) -> KnowledgeBase:
        kb = await self.ensure_default_kb(db)
        chunk_count = (
            await db.execute(
                select(func.count()).select_from(KnowledgeChunk).where(
                    KnowledgeChunk.knowledge_base_id == kb.id
                )
            )
        ).scalar_one()
        if int(chunk_count or 0) == 0:
            await self.ingest_paths(db, kb_name=kb.name, paths=DEFAULT_SOURCES)
        return kb

    async def list_bases(self, db: AsyncSession) -> list[KnowledgeBase]:
        return (await db.execute(select(KnowledgeBase).order_by(KnowledgeBase.name))).scalars().all()

    async def create_base(
        self,
        db: AsyncSession,
        *,
        name: str,
        description: str = "",
    ) -> KnowledgeBase:
        kb = KnowledgeBase(name=name, description=description)
        db.add(kb)
        await db.flush()
        return kb

    async def ingest_paths(self, db: AsyncSession, *, kb_name: str, paths: list[Path]) -> dict[str, Any]:
        kb = (
            await db.execute(select(KnowledgeBase).where(KnowledgeBase.name == kb_name))
        ).scalar_one_or_none()
        if kb is None:
            kb = await self.create_base(db, name=kb_name, description="")

        inserted = 0
        skipped = 0
        pending_rows: list[dict[str, Any]] = []
        for path in paths:
            if not path.exists():
                continue
            file_chunks = await asyncio.to_thread(_load_file_chunks, path)
            for title, content, meta in file_chunks:
                content_hash = _sha256(f"{path}:{title}:{content}")
                tf, count = term_frequencies(content)
                pending_rows.append(
                    {
                        "knowledge_base_id": kb.id,
                        "source": str(path),
                        "source_type": "file",
                        "title": title,
                        "content": content,
                        "content_hash": content_hash,
                        "token_count": count,
                        "term_freqs": tf,
                        "metadata_json": meta,
                    }
                )

        for offset in range(0, len(pending_rows), _INGEST_BATCH_SIZE):
            batch = pending_rows[offset : offset + _INGEST_BATCH_SIZE]
            if not batch:
                continue
            stmt = (
                insert(KnowledgeChunk)
                .values(batch)
                .on_conflict_do_nothing(index_elements=["knowledge_base_id", "content_hash"])
            )
            result = await db.execute(stmt)
            inserted += int(result.rowcount or 0)

        skipped = max(0, len(pending_rows) - inserted)

        await self._recompute_stats(db, kb)
        await get_knowledge_search_cache().invalidate_kb_async(kb_name)
        return {"inserted": inserted, "skipped": skipped}

    async def reset_kb(self, db: AsyncSession, *, kb_name: str) -> None:
        kb = (
            await db.execute(select(KnowledgeBase).where(KnowledgeBase.name == kb_name))
        ).scalar_one_or_none()
        if kb is None:
            return
        await db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.knowledge_base_id == kb.id))
        kb.stats_json = {}
        await get_knowledge_search_cache().invalidate_kb_async(kb_name)

    async def search(
        self,
        db: AsyncSession,
        *,
        kb_name: str,
        query: str,
        top_k: int = 5,
        cefr_level: str | None = None,
        pos: str | None = None,
        min_score: float = 0.0,
    ) -> list[SearchHit]:
        if not query.strip():
            return []

        kb = (
            await db.execute(select(KnowledgeBase).where(KnowledgeBase.name == kb_name))
        ).scalar_one_or_none()
        if kb is None:
            return []

        cache = get_knowledge_search_cache()
        fetch_k = max(top_k, min(top_k * 4, 20))

        if settings.KNOWLEDGE_USE_FTS:
            from backend.app.modules.knowledge.fts_search import fts_search_chunks

            ranked = await fts_search_chunks(
                db,
                kb_id=kb.id,
                query=query,
                top_k=fetch_k,
            )
        else:
            ranked = await cache.search_indexed(
                db,
                kb=kb,
                query=query,
                top_k=fetch_k,
            )
        from backend.app.modules.knowledge.cefr_filters import chunk_matches_cefr

        score_floor = min_score
        if score_floor <= 0:
            score_floor = (
                settings.KNOWLEDGE_FTS_MIN_SCORE
                if settings.KNOWLEDGE_USE_FTS
                else settings.KNOWLEDGE_BM25_MIN_SCORE
            )

        hits: list[SearchHit] = []
        for chunk, score in ranked:
            if score < score_floor:
                continue
            if not chunk_matches_cefr(chunk.metadata_json, cefr_level=cefr_level, pos=pos):
                continue
            hits.append(SearchHit(chunk=chunk, score=score))
            if len(hits) >= top_k:
                break
        return hits

    async def _recompute_stats(self, db: AsyncSession, kb: KnowledgeBase) -> None:
        chunks = (
            await db.execute(select(KnowledgeChunk).where(KnowledgeChunk.knowledge_base_id == kb.id))
        ).scalars().all()
        if not chunks:
            kb.stats_json = {"doc_count": 0, "avg_doc_len": 0.0, "doc_freq": {}}
            return

        doc_count = len(chunks)
        total_len = 0
        df: dict[str, int] = {}
        for chunk in chunks:
            total_len += int(chunk.token_count or 0)
            for term in (chunk.term_freqs or {}).keys():
                df[term] = df.get(term, 0) + 1

        kb.stats_json = {
            "doc_count": doc_count,
            "avg_doc_len": float(total_len) / float(doc_count),
            "doc_freq": df,
            "updated_at": _now().isoformat(),
        }


_service: KnowledgeService | None = None


def get_knowledge_service() -> KnowledgeService:
    global _service
    if _service is None:
        _service = KnowledgeService()
    return _service
