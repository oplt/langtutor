from __future__ import annotations

import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)

_ANSWER_CACHE_TTL_SECONDS = 120
_REDIS_PREFIX = "rag:answer:"


def _cache_key(
    *,
    user_id: str,
    project_id: str | None,
    query: str,
    top_k: int,
    policy_revision: str,
) -> str:
    normalized = " ".join(query.strip().lower().split())
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    project = project_id or "_"
    return f"{_REDIS_PREFIX}{user_id}:{project}:{top_k}:{policy_revision}:{digest}"


async def get_cached_rag_answer(
    *,
    user_id: str,
    project_id: str | None,
    query: str,
    top_k: int,
    policy_revision: str,
) -> dict[str, Any] | None:
    from backend.app.core.redis_json import redis_get_json

    key = _cache_key(
        user_id=user_id,
        project_id=project_id,
        query=query,
        top_k=top_k,
        policy_revision=policy_revision,
    )
    cached = await redis_get_json(key)
    return cached if isinstance(cached, dict) else None


async def set_cached_rag_answer(
    *,
    user_id: str,
    project_id: str | None,
    query: str,
    top_k: int,
    policy_revision: str,
    payload: dict[str, Any],
) -> None:
    from backend.app.core.redis_json import redis_set_json

    key = _cache_key(
        user_id=user_id,
        project_id=project_id,
        query=query,
        top_k=top_k,
        policy_revision=policy_revision,
    )
    await redis_set_json(key, payload, ttl_seconds=_ANSWER_CACHE_TTL_SECONDS)
