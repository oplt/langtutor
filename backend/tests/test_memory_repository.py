from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock

from backend.app.modules.memory.repository import (
    MemoryRepository,
    reset_defaults_ensured_cache_for_tests,
)
from backend.app.modules.memory.types import L2_SURFACES, L3_SLOTS


def test_ensure_defaults_batches_insert_once() -> None:
    async def _run() -> None:
        reset_defaults_ensured_cache_for_tests()
        repo = MemoryRepository()
        db = AsyncMock()
        user_id = uuid.uuid4()

        await repo.ensure_defaults(db, user_id)
        await repo.ensure_defaults(db, user_id)

        assert db.execute.await_count == 1
        assert db.flush.await_count == 1

    asyncio.run(_run())


def test_ensure_defaults_covers_all_default_documents() -> None:
    assert len(L2_SURFACES) + len(L3_SLOTS) == 9


def test_reset_defaults_cache_allows_second_insert() -> None:
    async def _run() -> None:
        reset_defaults_ensured_cache_for_tests()
        repo = MemoryRepository()
        db = AsyncMock()
        user_id = uuid.uuid4()
        await repo.ensure_defaults(db, user_id)
        reset_defaults_ensured_cache_for_tests()
        await repo.ensure_defaults(db, user_id)
        assert db.execute.await_count == 2

    asyncio.run(_run())
