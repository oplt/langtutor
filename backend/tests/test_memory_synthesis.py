from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import InvalidRequestError

from backend.app.modules.memory.service import MemoryService


def test_synthesize_l3_reads_repository_sequentially():
    """Regression: one AsyncSession must not run concurrent repository queries."""
    service = MemoryService()
    user_id = uuid.uuid4()
    db = AsyncMock()

    active_reads = 0
    max_concurrent_reads = 0

    async def _track_read(*_args, **_kwargs):
        nonlocal active_reads, max_concurrent_reads
        active_reads += 1
        max_concurrent_reads = max(max_concurrent_reads, active_reads)
        await asyncio.sleep(0.01)
        active_reads -= 1
        return []

    service._repo.ensure_defaults = AsyncMock()
    service._repo.list_traces = AsyncMock(side_effect=_track_read)
    service._repo.list_documents = AsyncMock(side_effect=_track_read)
    service._repo.get_or_create_document = AsyncMock(
        return_value=SimpleNamespace(content="", entries_json=[])
    )
    service._repo.entries_from_row = MagicMock(return_value=[])
    service._repo.set_entries = MagicMock()
    service._repo.save_document = AsyncMock()

    async def _run() -> dict[str, str]:
        with (
            patch.object(service, "_build_profile_content", new=AsyncMock(return_value="- profile")),
            patch.object(service, "_build_scope", new=AsyncMock(return_value="- scope")),
            patch(
                "backend.app.modules.memory.service.invalidate_l3_read_cache_async",
                new=AsyncMock(),
            ),
            patch(
                "backend.app.modules.memory.service.set_l3_read_cache",
                new=AsyncMock(),
            ),
        ):
            return await service.synthesize_l3(db, user_id=user_id)

    result = asyncio.run(_run())

    assert result["recent"].startswith("-")
    assert max_concurrent_reads == 1
    assert service._repo.list_traces.await_count == 1
    assert service._repo.list_documents.await_count == 2


def test_run_synthesize_l3_logs_failure_with_traceback(caplog):
    from backend.app.modules.memory import tasks as memory_tasks

    user_id = uuid.uuid4()
    caplog.set_level("ERROR", logger="backend.app.modules.memory.tasks")

    with (
        patch.object(memory_tasks, "try_acquire_job_lock", new=AsyncMock(return_value=True)),
        patch.object(memory_tasks, "release_job_lock", new=AsyncMock()),
        patch.object(memory_tasks, "record_dead_letter", new=AsyncMock()),
        patch.object(memory_tasks, "session_scope") as session_scope_mock,
        patch.object(memory_tasks, "get_memory_service") as service_mock,
    ):
        db = AsyncMock()
        session_scope_mock.return_value.__aenter__ = AsyncMock(return_value=db)
        session_scope_mock.return_value.__aexit__ = AsyncMock(return_value=False)
        service_mock.return_value.synthesize_l3 = AsyncMock(
            side_effect=InvalidRequestError(
                "This session is provisioning a new connection; concurrent operations are not permitted"
            )
        )

        asyncio.run(memory_tasks._run_synthesize_l3(user_id))

    failed_logs = [r for r in caplog.records if r.getMessage() == "memory_synthesize_failed"]
    assert len(failed_logs) == 1
    assert failed_logs[0].exc_info is not None
    assert failed_logs[0].exc_info[0] is InvalidRequestError
    assert failed_logs[0].user_id == str(user_id)
