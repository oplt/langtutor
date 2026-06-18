from __future__ import annotations

import asyncio
import json

from backend.app.core.dead_letter import DEAD_LETTER_MAX_ITEMS, record_dead_letter


class FakeRedis:
    def __init__(self) -> None:
        self.pushed: list[tuple[str, str]] = []
        self.trimmed: list[tuple[str, int, int]] = []

    async def lpush(self, key: str, value: str) -> None:
        self.pushed.append((key, value))

    async def ltrim(self, key: str, start: int, stop: int) -> None:
        self.trimmed.append((key, start, stop))


def test_record_dead_letter_writes_capped_redis_list(monkeypatch) -> None:
    async def _run() -> None:
        redis = FakeRedis()
        monkeypatch.setattr("backend.app.core.redis.get_redis", lambda: redis)

        assert await record_dead_letter("persistence", {"turn_id": "t1"}) is True

        assert redis.pushed[0][0] == "dead_letter:persistence"
        entry = json.loads(redis.pushed[0][1])
        assert entry["queue"] == "persistence"
        assert entry["payload"] == {"turn_id": "t1"}
        assert redis.trimmed == [("dead_letter:persistence", 0, DEAD_LETTER_MAX_ITEMS - 1)]

    asyncio.run(_run())
