from __future__ import annotations

import asyncio
import logging
import uuid

from backend.app.core.background import schedule_background
from backend.app.core.redis_lock import release_job_lock, try_acquire_job_lock
from backend.app.db.session import session_scope
from backend.app.modules.memory.service import get_memory_service

logger = logging.getLogger(__name__)

_L3_LOCK_TTL_SECONDS = 1800
_scheduled_tasks: dict[str, asyncio.Task[None]] = {}


def _lock_key(user_id: uuid.UUID) -> str:
    return f"jobs:memory:l3:{user_id}"


async def _run_synthesize_l3(user_id: uuid.UUID) -> None:
    user_key = str(user_id)
    lock_key = _lock_key(user_id)
    try:
        async with session_scope() as db:
            await get_memory_service().synthesize_l3(db, user_id=user_id)
        logger.info("memory_synthesize_complete user_id=%s", user_key)
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
    logger.info("memory_synthesize_scheduled user_id=%s", user_key)
    return True
