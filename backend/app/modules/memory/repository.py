from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.modules.memory.models import UserMemoryDocument, UserMemoryTrace
from backend.app.modules.memory.types import L2_SURFACES, L3_SLOTS, MemoryEntry

_DEFAULTS_CACHE_VERSION = 1
_defaults_ensured_users: set[tuple[int, uuid.UUID]] = set()


def reset_defaults_ensured_cache_for_tests() -> None:
    _defaults_ensured_users.clear()


class MemoryRepository:
    async def append_trace(self, db: AsyncSession, **fields: Any) -> UserMemoryTrace:
        row = UserMemoryTrace(**fields)
        db.add(row)
        await db.flush()
        return row

    async def trim_user_traces(self, db: AsyncSession, *, user_id: uuid.UUID) -> None:
        from sqlalchemy import delete, select

        from backend.app.modules.memory.types import MAX_TRACE_STORE

        keep_ids = (
            select(UserMemoryTrace.id)
            .where(UserMemoryTrace.user_id == user_id)
            .order_by(UserMemoryTrace.created_at.desc())
            .limit(MAX_TRACE_STORE)
        )
        await db.execute(
            delete(UserMemoryTrace).where(
                UserMemoryTrace.user_id == user_id,
                UserMemoryTrace.id.not_in(keep_ids),
            )
        )
        await db.flush()

    async def list_users_over_trace_limit(
        self,
        db: AsyncSession,
        *,
        limit: int = 50,
    ) -> list[uuid.UUID]:
        from sqlalchemy import func

        from backend.app.modules.memory.types import MAX_TRACE_STORE

        stmt = (
            select(UserMemoryTrace.user_id)
            .group_by(UserMemoryTrace.user_id)
            .having(func.count(UserMemoryTrace.id) > MAX_TRACE_STORE)
            .limit(max(1, limit))
        )
        rows = (await db.execute(stmt)).scalars().all()
        return list(rows)

    async def count_traces(self, db: AsyncSession, *, user_id: uuid.UUID) -> int:
        from sqlalchemy import func

        count = (
            await db.execute(
                select(func.count())
                .select_from(UserMemoryTrace)
                .where(UserMemoryTrace.user_id == user_id)
            )
        ).scalar_one()
        return int(count or 0)

    async def list_traces(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        surface: str | None = None,
        limit: int = 100,
    ) -> list[UserMemoryTrace]:
        q = select(UserMemoryTrace).where(UserMemoryTrace.user_id == user_id)
        if surface:
            q = q.where(UserMemoryTrace.surface == surface)
        q = q.order_by(UserMemoryTrace.created_at.desc()).limit(limit)
        return list((await db.execute(q)).scalars().all())

    async def get_document(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        layer: str,
        doc_key: str,
    ) -> UserMemoryDocument | None:
        return (
            await db.execute(
                select(UserMemoryDocument)
                .where(UserMemoryDocument.user_id == user_id)
                .where(UserMemoryDocument.layer == layer)
                .where(UserMemoryDocument.doc_key == doc_key)
            )
        ).scalar_one_or_none()

    async def get_or_create_document(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        layer: str,
        doc_key: str,
    ) -> UserMemoryDocument:
        row = await self.get_document(db, user_id=user_id, layer=layer, doc_key=doc_key)
        if row is not None:
            return row
        row = UserMemoryDocument(user_id=user_id, layer=layer, doc_key=doc_key, content="")
        db.add(row)
        await db.flush()
        return row

    async def save_document(self, db: AsyncSession, row: UserMemoryDocument) -> None:
        row.version += 1
        await db.flush()

    async def list_documents(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        layer: str | None = None,
    ) -> list[UserMemoryDocument]:
        q = select(UserMemoryDocument).where(UserMemoryDocument.user_id == user_id)
        if layer:
            q = q.where(UserMemoryDocument.layer == layer)
        q = q.order_by(UserMemoryDocument.layer, UserMemoryDocument.doc_key)
        return list((await db.execute(q)).scalars().all())

    def entries_from_row(self, row: UserMemoryDocument) -> list[MemoryEntry]:
        raw = row.entries if isinstance(row.entries, list) else []
        return [MemoryEntry.from_dict(item) for item in raw if isinstance(item, dict)]

    def set_entries(self, row: UserMemoryDocument, entries: list[MemoryEntry]) -> None:
        row.entries = [entry.to_dict() for entry in entries]
        row.content = _render_entries(entries)

    async def ensure_defaults(self, db: AsyncSession, user_id: uuid.UUID) -> None:
        cache_key = (_DEFAULTS_CACHE_VERSION, user_id)
        if await self._defaults_already_ensured(user_id):
            return

        rows = [
            {
                "user_id": user_id,
                "layer": "L2",
                "doc_key": surface,
                "content": "",
                "entries": [],
                "version": 0,
            }
            for surface in L2_SURFACES
        ] + [
            {
                "user_id": user_id,
                "layer": "L3",
                "doc_key": slot,
                "content": "",
                "entries": [],
                "version": 0,
            }
            for slot in L3_SLOTS
        ]

        stmt = insert(UserMemoryDocument).values(rows)
        stmt = stmt.on_conflict_do_nothing(constraint="uq_user_memory_doc")
        await db.execute(stmt)
        await db.flush()
        await self._mark_defaults_ensured(user_id)

    async def _defaults_already_ensured(self, user_id: uuid.UUID) -> bool:
        cache_key = (_DEFAULTS_CACHE_VERSION, user_id)
        if cache_key in _defaults_ensured_users:
            return True
        try:
            from backend.app.core.redis import get_redis

            return bool(
                await get_redis().sismember(
                    f"memory:defaults:{_DEFAULTS_CACHE_VERSION}",
                    str(user_id),
                )
            )
        except Exception:
            return False

    async def _mark_defaults_ensured(self, user_id: uuid.UUID) -> None:
        cache_key = (_DEFAULTS_CACHE_VERSION, user_id)
        _defaults_ensured_users.add(cache_key)
        try:
            from backend.app.core.redis import get_redis

            await get_redis().sadd(f"memory:defaults:{_DEFAULTS_CACHE_VERSION}", str(user_id))
        except Exception:
            return


def _render_entries(entries: list[MemoryEntry]) -> str:
    if not entries:
        return ""
    lines = []
    for entry in entries:
        suffix = f" <!--{entry.id}-->" if entry.id else ""
        lines.append(f"- {entry.text}{suffix}")
    return "\n".join(lines)
