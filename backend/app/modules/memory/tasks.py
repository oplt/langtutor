from __future__ import annotations

import asyncio
import logging
import time
import uuid

from backend.app.core.background import schedule_background
from backend.app.core.config import settings
from backend.app.core.dead_letter import record_dead_letter
from backend.app.core.redis_lock import release_job_lock, try_acquire_job_lock
from backend.app.db.session import session_scope
from backend.app.modules.memory.service import get_memory_service

logger = logging.getLogger(__name__)

_L3_LOCK_TTL_SECONDS = 1800
_L3_SYNTHESIZE_MAX_ATTEMPTS = 3
_TRACE_TRIM_INTERVAL_SECONDS = 300
_TRACE_TRIM_BATCH_USERS = 50
_scheduled_tasks: dict[str, asyncio.Task[None]] = {}
_maintenance_task: asyncio.Task[None] | None = None


def _lock_key(user_id: uuid.UUID) -> str:
    return f"jobs:memory:l3:{user_id}"


async def _run_synthesize_l3(user_id: uuid.UUID) -> None:
    user_key = str(user_id)
    lock_key = _lock_key(user_id)
    last_error: Exception | None = None
    started = time.perf_counter()
    logger.info("memory_synthesize_started", extra={"user_id": user_key})
    try:
        for attempt in range(1, _L3_SYNTHESIZE_MAX_ATTEMPTS + 1):
            try:
                async with session_scope() as db:
                    await get_memory_service().synthesize_l3(db, user_id=user_id)
                duration_ms = round((time.perf_counter() - started) * 1000, 2)
                extra = {"user_id": user_key, "duration_ms": duration_ms}
                if duration_ms >= settings.SLOW_JOB_MS:
                    logger.warning("memory_synthesize_slow", extra=extra)
                else:
                    logger.info("memory_synthesize_complete", extra=extra)
                return
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "memory_synthesize_retry",
                    extra={
                        "user_id": user_key,
                        "task": "memory_synthesize_l3",
                        "attempt": attempt,
                        "max_attempts": _L3_SYNTHESIZE_MAX_ATTEMPTS,
                    },
                    exc_info=True,
                )
                if attempt < _L3_SYNTHESIZE_MAX_ATTEMPTS:
                    await asyncio.sleep(0.25 * attempt)

        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.error(
            "memory_synthesize_failed",
            extra={
                "user_id": user_key,
                "task": "memory_synthesize_l3",
                "attempts": _L3_SYNTHESIZE_MAX_ATTEMPTS,
                "duration_ms": duration_ms,
                "error_type": last_error.__class__.__name__ if last_error else "Unknown",
            },
            exc_info=(
                (type(last_error), last_error, last_error.__traceback__)
                if last_error is not None
                else False
            ),
        )
        await record_dead_letter(
            "memory_l3_synthesis",
            {
                "user_id": user_key,
                "error_type": last_error.__class__.__name__ if last_error else "Unknown",
                "error": str(last_error) if last_error else "",
            },
        )
    finally:
        await release_job_lock(lock_key)
        _scheduled_tasks.pop(user_key, None)


async def enqueue_synthesize_l3(user_id: uuid.UUID) -> bool:
    """
    Schedule L3 memory synthesis off the request path.

    Returns True when a new background task is scheduled, False when one is already pending.
    """
    user_key = str(user_id)
    existing = _scheduled_tasks.get(user_key)
    if existing is not None and not existing.done():
        return False

    if not await try_acquire_job_lock(_lock_key(user_id), ttl_seconds=_L3_LOCK_TTL_SECONDS):
        return False

    task = schedule_background(
        _run_synthesize_l3(user_id),
        name=f"memory_synthesize_l3:{user_key}",
    )
    _scheduled_tasks[user_key] = task
    logger.info("memory_synthesize_scheduled", extra={"user_id": user_key})
    return True


async def run_trace_trim_cycle() -> int:
    from backend.app.modules.memory.repository import MemoryRepository

    repo = MemoryRepository()
    trimmed_users = 0
    async with session_scope() as db:
        user_ids = await repo.list_users_over_trace_limit(
            db, limit=_TRACE_TRIM_BATCH_USERS
        )
        for user_id in user_ids:
            await repo.trim_user_traces(db, user_id=user_id)
            trimmed_users += 1
    if trimmed_users:
        logger.info("memory_trace_trim_cycle users=%s", trimmed_users)
    return trimmed_users


async def _memory_maintenance_loop() -> None:
    while True:
        try:
            await run_trace_trim_cycle()
        except Exception:
            logger.exception("memory_maintenance_cycle_failed")
        await asyncio.sleep(_TRACE_TRIM_INTERVAL_SECONDS)


def start_memory_maintenance() -> None:
    global _maintenance_task
    if _maintenance_task is not None and not _maintenance_task.done():
        return
    _maintenance_task = schedule_background(
        _memory_maintenance_loop(),
        name="memory_maintenance",
    )
    logger.info("memory_maintenance_started")
