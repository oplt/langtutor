from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.modules.memory.l3_cache import (
    get_l3_read_cache,
    get_l3_capability_cache,
    invalidate_l3_read_cache_async,
    set_l3_read_cache,
    set_l3_capability_cache,
)
from backend.app.modules.memory.repository import MemoryRepository, _render_entries
from backend.app.modules.memory.types import (
    CAPABILITY_L3_SLOT_ORDER,
    L2_SURFACES,
    L3_SLOTS,
    MAX_ENTRY_CHARS,
    MAX_L2_ENTRIES,
    MAX_TRACE_FETCH,
    MemoryEntry,
    TraceEvent,
)

logger = logging.getLogger(__name__)

_L3_SECTION = re.compile(r"^###\s+(.+)$", re.MULTILINE)


class MemoryService:
    def __init__(self) -> None:
        self._repo = MemoryRepository()

    async def emit(
        self,
        db: AsyncSession,
        *,
        user_id,
        event: TraceEvent,
        promote_l2: bool = True,
    ) -> None:
        await self._repo.append_trace(db, **event.to_row_kwargs(user_id))
        if promote_l2:
            fact = _fact_from_trace(event)
            if fact:
                await self.append_l2_fact(
                    db,
                    user_id=user_id,
                    surface=event.surface,
                    text=fact,
                    source=event.kind,
                    ref=event.turn_id or event.session_id,
                )

    async def append_l2_fact(
        self,
        db: AsyncSession,
        *,
        user_id,
        surface: str,
        text: str,
        source: str = "",
        ref: str = "",
    ) -> MemoryEntry:
        cleaned = text.strip()[:MAX_ENTRY_CHARS]
        if not cleaned:
            raise ValueError("empty_fact")
        if surface not in L2_SURFACES:
            surface = "tutor"
        row = await self._repo.get_or_create_document(
            db, user_id=user_id, layer="L2", doc_key=surface
        )
        entries = self._repo.entries_from_row(row)
        entry = MemoryEntry(
            id=f"m_{uuid4().hex[:12]}",
            text=cleaned,
            created_at=datetime.now(UTC).isoformat(),
            source=source,
            ref=ref,
        )
        entries.append(entry)
        if len(entries) > MAX_L2_ENTRIES:
            entries = entries[-MAX_L2_ENTRIES:]
        self._repo.set_entries(row, entries)
        await self._repo.save_document(db, row)
        return entry

    async def write_preference(
        self,
        db: AsyncSession,
        *,
        user_id,
        text: str,
        op: str = "add",
        target_id: str = "",
    ) -> MemoryEntry:
        row = await self._repo.get_or_create_document(
            db, user_id=user_id, layer="L3", doc_key="preferences"
        )
        entries = self._repo.entries_from_row(row)
        cleaned = text.strip()[:MAX_ENTRY_CHARS]
        if not cleaned:
            raise ValueError("empty_preference")
        if op == "edit" and target_id:
            updated = False
            for entry in entries:
                if entry.id == target_id:
                    entry.text = cleaned
                    updated = True
                    break
            if not updated:
                raise ValueError("entry_not_found")
        else:
            entries.append(
                MemoryEntry(
                    id=f"m_{uuid4().hex[:12]}",
                    text=cleaned,
                    created_at=datetime.now(UTC).isoformat(),
                    source="write_memory",
                )
            )
        self._repo.set_entries(row, entries)
        await self._repo.save_document(db, row)
        await invalidate_l3_read_cache_async(user_id)
        return entries[-1]

    async def read_l3_concat(
        self,
        db: AsyncSession,
        *,
        user_id,
        use_cache: bool = True,
        capability: str | None = None,
    ) -> str:
        if use_cache and capability:
            cached = await get_l3_capability_cache(user_id, capability)
            if cached is not None:
                return cached
        elif use_cache:
            cached = await get_l3_read_cache(user_id)
            if cached is not None:
                return cached

        await self._repo.ensure_defaults(db, user_id)
        docs = await self._repo.list_documents(db, user_id=user_id, layer="L3")
        by_key = {doc.doc_key: doc for doc in docs}
        slot_order = CAPABILITY_L3_SLOT_ORDER.get(capability or "", L3_SLOTS)
        parts: list[str] = []
        for slot in slot_order:
            if slot not in L3_SLOTS:
                continue
            row = by_key.get(slot)
            if row and row.content.strip():
                parts.append(f"### {slot}\n{row.content.strip()}")
        text = "\n\n".join(parts)
        if use_cache and capability:
            await set_l3_capability_cache(user_id, capability, text)
        elif use_cache:
            await set_l3_read_cache(user_id, text)
        return text

    async def read_l3_for_query(
        self,
        db: AsyncSession,
        *,
        user_id,
        query: str,
        capability: str | None = None,
        max_chars: int = 2400,
    ) -> str:
        full = await self.read_l3_concat(
            db,
            user_id=user_id,
            use_cache=True,
            capability=capability,
        )
        if not full.strip() or not query.strip():
            return full

        from backend.app.modules.knowledge.bm25 import tokenize

        terms = {term for term in tokenize(query) if len(term) >= 3}
        if not terms:
            return full[:max_chars]

        sections = _L3_SECTION.split(full)
        if len(sections) <= 1:
            return full[:max_chars]

        scored: list[tuple[int, str]] = []
        for idx in range(1, len(sections), 2):
            title = sections[idx].strip()
            body = sections[idx + 1].strip() if idx + 1 < len(sections) else ""
            if not body:
                continue
            blob = f"{title} {body}".lower()
            score = sum(1 for term in terms if term in blob)
            if score <= 0:
                continue
            scored.append((score, f"### {title}\n{body}"))

        if not scored or max(item[0] for item in scored) == 0:
            return full[:max_chars]

        scored.sort(key=lambda item: item[0], reverse=True)
        parts: list[str] = []
        used = 0
        for _, section in scored:
            if used + len(section) > max_chars and parts:
                break
            parts.append(section)
            used += len(section) + 2
        return "\n\n".join(parts) if parts else full[:max_chars]

    async def synthesize_l3(self, db: AsyncSession, *, user_id) -> dict[str, str]:
        await self._repo.ensure_defaults(db, user_id)
        traces = await self._repo.list_traces(db, user_id=user_id, limit=MAX_TRACE_FETCH)
        l2_docs = await self._repo.list_documents(db, user_id=user_id, layer="L2")
        l3_docs = await self._repo.list_documents(db, user_id=user_id, layer="L3")
        l3_by_key = {doc.doc_key: doc for doc in l3_docs}

        recent_lines = []
        for trace in traces[:12]:
            summary = _trace_summary(trace)
            if summary:
                recent_lines.append(f"- {summary}")
        recent_content = "\n".join(recent_lines) if recent_lines else "- No recent activity yet."

        profile_lines = []
        for doc in l2_docs:
            for entry in self._repo.entries_from_row(doc)[-5:]:
                profile_lines.append(f"- [{doc.doc_key}] {entry.text}")
        profile_content = await self._build_profile_content(
            profile_lines=profile_lines,
            traces=traces,
        )

        scope_content = await self._build_scope(db, user_id=user_id, traces=traces)

        await self._set_l3_slot(
            db, user_id=user_id, slot="recent", content=recent_content, row=l3_by_key.get("recent")
        )
        await self._set_l3_slot(
            db, user_id=user_id, slot="profile", content=profile_content, row=l3_by_key.get("profile")
        )
        await self._set_l3_slot(
            db, user_id=user_id, slot="scope", content=scope_content, row=l3_by_key.get("scope")
        )

        parts: list[str] = []
        for slot, content in (
            ("recent", recent_content),
            ("profile", profile_content),
            ("scope", scope_content),
        ):
            if content.strip():
                parts.append(f"### {slot}\n{content.strip()}")
        merged = "\n\n".join(parts)
        await invalidate_l3_read_cache_async(user_id)
        await set_l3_read_cache(user_id, merged)

        return {
            "recent": recent_content,
            "profile": profile_content,
            "scope": scope_content,
        }

    async def overview(self, db: AsyncSession, *, user_id) -> dict:
        await self._repo.ensure_defaults(db, user_id)
        l2 = await self._repo.list_documents(db, user_id=user_id, layer="L2")
        l3 = await self._repo.list_documents(db, user_id=user_id, layer="L3")
        trace_count = await self._repo.count_traces(db, user_id=user_id)
        return {
            "trace_count": trace_count,
            "l2": [
                {
                    "surface": doc.doc_key,
                    "entry_count": len(self._repo.entries_from_row(doc)),
                    "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
                }
                for doc in l2
            ],
            "l3": [
                {
                    "slot": doc.doc_key,
                    "entry_count": len(self._repo.entries_from_row(doc)),
                    "preview": doc.content[:200],
                    "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
                }
                for doc in l3
            ],
        }

    async def get_l2(self, db: AsyncSession, *, user_id, surface: str) -> dict:
        row = await self._repo.get_or_create_document(
            db, user_id=user_id, layer="L2", doc_key=surface
        )
        return {
            "surface": surface,
            "content": row.content,
            "entries": [entry.to_dict() for entry in self._repo.entries_from_row(row)],
        }

    async def get_l3_slot(self, db: AsyncSession, *, user_id, slot: str) -> dict:
        row = await self._repo.get_or_create_document(
            db, user_id=user_id, layer="L3", doc_key=slot
        )
        return {
            "slot": slot,
            "content": row.content,
            "entries": [entry.to_dict() for entry in self._repo.entries_from_row(row)],
        }

    async def _set_l3_slot(
        self,
        db: AsyncSession,
        *,
        user_id,
        slot: str,
        content: str,
        row=None,
    ) -> None:
        if slot == "preferences":
            return
        if row is None:
            row = await self._repo.get_or_create_document(
                db, user_id=user_id, layer="L3", doc_key=slot
            )
        entries = [
            MemoryEntry(
                id=f"m_{uuid4().hex[:12]}",
                text=line.removeprefix("- ").strip(),
                created_at=datetime.now(UTC).isoformat(),
                source="synthesize",
            )
            for line in content.splitlines()
            if line.strip().startswith("-")
        ]
        self._repo.set_entries(row, entries)
        row.content = _render_entries(entries)
        await self._repo.save_document(db, row)

    async def _build_scope(self, db: AsyncSession, *, user_id, traces: list) -> str:
        cefr = ""
        for trace in traces:
            payload = trace.payload or {}
            if payload.get("cefr_level"):
                cefr = str(payload["cefr_level"])
                break
        lines = [f"- Active CEFR focus: {cefr or 'unknown'}"]
        try:
            from sqlalchemy import func, select

            from backend.app.modules.learning.models import UserWordProgress, Word

            mastered = (
                await db.execute(
                    select(func.count(UserWordProgress.id))
                    .join(Word, Word.id == UserWordProgress.word_id)
                    .where(UserWordProgress.user_id == user_id)
                    .where(UserWordProgress.recognition_strength >= 60)
                    .where(UserWordProgress.recall_strength >= 60)
                )
            ).scalar_one_or_none()
            lines.append(f"- Mastered vocabulary items: {mastered or 0}")
        except Exception:
            logger.warning("memory_scope_vocab_count_failed user_id=%s", user_id, exc_info=True)
        surfaces = {trace.surface for trace in traces[:50]}
        if surfaces:
            lines.append(f"- Active learning surfaces: {', '.join(sorted(surfaces))}")
        return "\n".join(lines)

    async def _build_profile_content(self, *, profile_lines: list[str], traces: list) -> str:
        baseline = "\n".join(profile_lines[:25]) if profile_lines else "- Still learning your patterns."
        if not settings.MEMORY_L3_LLM_PROFILE or not settings.AI_AGENT_ENABLED:
            return baseline

        trace_hints = [_trace_summary(trace) for trace in traces[:8]]
        if not trace_hints and profile_lines:
            return baseline

        prompt = (
            "Summarize this Dutch learner's patterns in 3-5 bullet lines for a tutor memory slot. "
            "Be factual; do not invent progress.\n\n"
            f"Recent activity:\n" + "\n".join(f"- {line}" for line in trace_hints if line) + "\n\n"
            f"Existing notes:\n{baseline}"
        )
        try:
            from backend.app.modules.llm.base import LLMChatRequest, LLMMessage
            from backend.app.modules.llm.service import create_task_client

            client = await create_task_client("memory_synthesis")
            response = await client.chat(
                LLMChatRequest(
                    messages=[LLMMessage(role="user", content=prompt)],
                    max_tokens=settings.MEMORY_L3_PROFILE_MAX_TOKENS,
                )
            )
            text = (response.content or "").strip()
            if text:
                evidence = profile_lines[:25] + [line for line in trace_hints if line]
                grounded = _ground_profile_text(text, evidence)
                if grounded:
                    return grounded
        except Exception:
            logger.warning("memory_profile_llm_synthesis_failed", exc_info=True)
        return baseline


def _ground_profile_text(text: str, evidence_lines: list[str]) -> str:
    evidence_tokens: set[str] = set()
    for line in evidence_lines:
        for token in re.findall(r"[a-zA-Z'\-]{3,}", line.lower()):
            evidence_tokens.add(token)
    if not evidence_tokens:
        return ""
    kept: list[str] = []
    for line in text.splitlines():
        stripped = line.strip().lstrip("-•* ").strip()
        if not stripped:
            continue
        line_tokens = set(re.findall(r"[a-zA-Z'\-]{3,}", stripped.lower()))
        if line_tokens & evidence_tokens:
            kept.append(stripped if stripped.startswith("-") else f"- {stripped}")
    return "\n".join(kept)


def _fact_from_trace(event: TraceEvent) -> str:
    payload = event.payload or {}
    if event.kind == "quiz_answer":
        lemma = str(payload.get("lemma") or "")
        if payload.get("correct") is False and lemma:
            return f"Struggled with '{lemma}' in {payload.get('exercise_type', 'quiz')}."
        if payload.get("correct") is True and lemma:
            return f"Answered correctly on '{lemma}'."
    if event.kind == "turn_complete":
        preview = str(payload.get("user_message") or "")[:80]
        if preview:
            return f"Discussed: {preview}"
    if event.kind == "preference":
        return str(payload.get("text") or "")
    return ""


def _trace_summary(trace) -> str:
    payload = trace.payload or {}
    if trace.kind == "quiz_answer":
        lemma = payload.get("lemma") or "word"
        verdict = "correct" if payload.get("correct") else "incorrect"
        return f"[{trace.surface}] {lemma} — {verdict}"
    if trace.kind == "turn_complete":
        msg = str(payload.get("user_message") or "")[:60]
        return f"[{trace.surface}] {msg}" if msg else f"[{trace.surface}] tutor turn"
    return f"[{trace.surface}] {trace.kind}"


_service: MemoryService | None = None


def get_memory_service() -> MemoryService:
    global _service
    if _service is None:
        _service = MemoryService()
    return _service
