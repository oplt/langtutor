from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.modules.memory import tasks as memory_tasks


@pytest.fixture(autouse=True)
def _reset_memory_task_state() -> None:
    memory_tasks._scheduled_tasks.clear()
    yield
    memory_tasks._scheduled_tasks.clear()


def test_enqueue_synthesize_l3_deduplicates(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        user_id = uuid.uuid4()
        scheduled: list[str] = []

        def _fake_schedule(coro, *, name: str) -> MagicMock:
            scheduled.append(name)
            coro.close()
            return MagicMock(done=MagicMock(return_value=False))

        monkeypatch.setattr(memory_tasks, "schedule_background", _fake_schedule)
        monkeypatch.setattr(
            memory_tasks,
            "try_acquire_job_lock",
            AsyncMock(return_value=True),
        )
        monkeypatch.setattr(memory_tasks, "release_job_lock", AsyncMock())

        assert await memory_tasks.enqueue_synthesize_l3(user_id) is True
        assert await memory_tasks.enqueue_synthesize_l3(user_id) is False
        assert len(scheduled) == 1
        assert scheduled[0] == f"memory_synthesize_l3:{user_id}"

    asyncio.run(_run())
