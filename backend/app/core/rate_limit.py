from __future__ import annotations

import time
from collections import deque

from redis.asyncio import Redis


class InMemoryFixedWindowLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, deque[float]] = {}

    def allow(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        now = time.time()
        bucket = self._buckets.setdefault(key, deque())
        cutoff = now - window_seconds
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            retry_after = max(1, int(window_seconds - (now - bucket[0])))
            return False, retry_after
        bucket.append(now)
        return True, 0


class RedisFixedWindowLimiter:
    def __init__(self, redis_client: Redis, namespace: str = "rl") -> None:
        self.redis = redis_client
        self.namespace = namespace

    async def allow(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        redis_key = f"{self.namespace}:{key}"
        count = await self.redis.incr(redis_key)
        if count == 1:
            await self.redis.expire(redis_key, window_seconds)
        if count <= limit:
            return True, 0

        ttl = await self.redis.ttl(redis_key)
        retry_after = int(ttl) if isinstance(ttl, int) and ttl > 0 else window_seconds
        return False, max(1, retry_after)
