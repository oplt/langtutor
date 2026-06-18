from __future__ import annotations

import asyncio

from backend.app.core.redis_lock import (
    release_job_lock,
    reset_job_locks_for_tests,
    try_acquire_job_lock,
)


def test_job_lock_memory_fallback_when_redis_unavailable(monkeypatch) -> None:
    async def _run() -> None:
        reset_job_locks_for_tests()

        def _fail():
            raise ConnectionError("redis down")

        monkeypatch.setattr("backend.app.core.redis.get_redis", _fail)

        assert await try_acquire_job_lock("jobs:test:1", ttl_seconds=60) is True
        assert await try_acquire_job_lock("jobs:test:1", ttl_seconds=60) is False
        await release_job_lock("jobs:test:1")
        assert await try_acquire_job_lock("jobs:test:1", ttl_seconds=60) is True

    asyncio.run(_run())
