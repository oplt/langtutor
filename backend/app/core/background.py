from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Coroutine
from typing import Any, TypeVar

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def _run_instrumented(coro: Coroutine[Any, Any, T], *, name: str) -> T:
    start = time.perf_counter()
    logger.info("background_task_started", extra={"task": name})
    try:
        result = await coro
    except asyncio.CancelledError:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.debug(
            "background_task_cancelled",
            extra={"task": name, "duration_ms": duration_ms},
        )
        raise
    except Exception:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.exception(
            "background_task_failed",
            extra={"task": name, "duration_ms": duration_ms},
        )
        raise
    else:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        extra = {"task": name, "duration_ms": duration_ms}
        if duration_ms >= settings.SLOW_JOB_MS:
            logger.warning("background_task_slow", extra=extra)
        else:
            logger.info("background_task_complete", extra=extra)
        return result


def schedule_background(coro: Coroutine[Any, Any, T], *, name: str) -> asyncio.Task[T]:
    """Run work outside the request lifecycle; log failures without crashing the server."""
    task = asyncio.create_task(_run_instrumented(coro, name=name), name=name)

    def _done(done: asyncio.Task[T]) -> None:
        try:
            done.result()
        except asyncio.CancelledError:
            return
        except Exception:
            return

    task.add_done_callback(_done)
    return task
