from __future__ import annotations

import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)

_CACHE_PREFIX = "translation:deepl:"
_CACHE_TTL_SECONDS = 86_400


def _cache_key(
    *,
    text: str,
    source_lang: str,
    target_lang: str,
    model_type: str | None,
) -> str:
    digest = hashlib.sha256(
        ":".join(
            [
                source_lang,
                target_lang,
                model_type or "",
                text,
            ]
        ).encode("utf-8")
    ).hexdigest()[:40]
    return f"{_CACHE_PREFIX}{digest}"


async def get_cached_translation(
    *,
    text: str,
    source_lang: str,
    target_lang: str,
    model_type: str | None,
) -> dict[str, Any] | None:
    from backend.app.core.redis_json import redis_get_json

    key = _cache_key(
        text=text,
        source_lang=source_lang,
        target_lang=target_lang,
        model_type=model_type,
    )
    try:
        cached = await redis_get_json(key)
    except Exception as exc:
        logger.debug("translation_cache_get_failed key=%s error=%s", key, exc)
        return None
    return cached if isinstance(cached, dict) else None


async def set_cached_translation(
    *,
    text: str,
    source_lang: str,
    target_lang: str,
    model_type: str | None,
    payload: dict[str, Any],
) -> None:
    from backend.app.core.redis_json import redis_set_json

    key = _cache_key(
        text=text,
        source_lang=source_lang,
        target_lang=target_lang,
        model_type=model_type,
    )
    try:
        await redis_set_json(key, payload, ttl_seconds=_CACHE_TTL_SECONDS)
    except Exception as exc:
        logger.debug("translation_cache_set_failed key=%s error=%s", key, exc)
