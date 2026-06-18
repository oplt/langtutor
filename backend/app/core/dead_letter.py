from __future__ import annotations

import json
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

DEAD_LETTER_MAX_ITEMS = 500


async def record_dead_letter(queue: str, payload: dict[str, Any]) -> bool:
    entry = {
        "queue": queue,
        "created_at": time.time(),
        "payload": payload,
    }
    try:
        from backend.app.core.redis import get_redis

        key = f"dead_letter:{queue}"
        redis = get_redis()
        await redis.lpush(key, json.dumps(entry, ensure_ascii=False, default=str))
        await redis.ltrim(key, 0, DEAD_LETTER_MAX_ITEMS - 1)
        return True
    except Exception:
        logger.warning("dead_letter_record_failed queue=%s", queue, exc_info=True)
        return False
