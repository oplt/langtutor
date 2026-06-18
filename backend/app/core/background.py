from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def schedule_background(coro: Coroutine[Any, Any, T], *, name: str) -> asyncio.Task[T]:
    """Run work outside the request lifecycle; log failures without crashing the server."""
    task = asyncio.create_task(coro, name=name)

    def _done(done: asyncio.Task[T]) -> None:
        try:
            done.result()
        except asyncio.CancelledError:
            logger.debug("Background task cancelled: %s", name)
        except Exception:
            logger.exception("Background task failed: %s", name)

    task.add_done_callback(_done)
    return task
