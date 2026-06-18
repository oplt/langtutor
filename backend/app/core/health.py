from __future__ import annotations

import logging
from typing import Any

from backend.app.core.config import settings
from backend.app.core.redis_registry import redis_feature_inventory
from backend.app.db.session import db_healthcheck

logger = logging.getLogger(__name__)


async def check_database() -> bool:
    try:
        await db_healthcheck()
        return True
    except Exception:
        logger.warning("health_check_database_failed", exc_info=True)
        return False


async def check_redis() -> bool:
    try:
        from backend.app.core.redis import get_redis

        pong = await get_redis().ping()
        return bool(pong)
    except Exception:
        logger.warning("health_check_redis_failed", exc_info=True)
        return False


async def check_llm() -> str:
    if not settings.AI_AGENT_ENABLED:
        return "disabled"
    try:
        from backend.app.modules.ai.service import AISettingsService

        profile = await AISettingsService().resolve_task_profile("tutor_chat")
        if not profile.enabled:
            return "profile_disabled"
        return "configured"
    except Exception:
        logger.warning("health_check_llm_failed", exc_info=True)
        return "unavailable"


async def readiness_report() -> dict[str, Any]:
    database = await check_database()
    redis = await check_redis()
    llm = await check_llm()
    ok = database
    report: dict[str, Any] = {
        "ok": ok,
        "checks": {
            "database": database,
            "redis": redis,
            "llm": llm,
        },
    }
    if redis:
        report["redis_features"] = redis_feature_inventory()
    else:
        report["redis_features"] = []
        report["redis_note"] = (
            "Redis unavailable; rate limits, OAuth state, tutor turns, caches, "
            "and job locks fall back to in-process storage."
        )
    return report
