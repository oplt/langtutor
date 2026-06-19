from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

logger = logging.getLogger(__name__)


def format_sse_event(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, default=str)}\n\n"


async def iter_sse_from_frames(frames: AsyncIterator[dict[str, Any]]) -> AsyncIterator[str]:
    async for frame in frames:
        yield format_sse_event(frame)
