from __future__ import annotations

import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)

_REDIS_PREFIX = "reading:generate:"
PROMPT_VERSION = "reading_generation_v9_compact_bounded_json"


def _hash_text(value: str, *, length: int = 24) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()[:length]


def _cache_key(
    *,
    level: int,
    interest_area: str,
    word_count: int,
    source_mode: str,
    strictness: str,
    source_title: str,
    source_url: str = "",
    source_published_at: str = "",
    source_content: str = "",
    language: str = "nl",
    translation_mode: str = "none",
    model_name: str = "",
    prompt_version: str = PROMPT_VERSION,
) -> str:
    normalized_title = " ".join(source_title.strip().lower().split())
    source_digest = _hash_text(f"{source_url}:{source_published_at}:{source_content}")
    digest = hashlib.sha256(
        ":".join(
            [
                str(level),
                language,
                translation_mode,
                interest_area,
                str(word_count),
                source_mode,
                strictness,
                normalized_title,
                source_digest,
                model_name or "default",
                prompt_version,
            ]
        ).encode("utf-8")
    ).hexdigest()[:32]
    return f"{_REDIS_PREFIX}{digest}"


async def get_cached_reading_generate(
    *,
    level: int,
    interest_area: str,
    word_count: int,
    source_mode: str,
    strictness: str,
    source_title: str,
    source_url: str = "",
    source_published_at: str = "",
    source_content: str = "",
    language: str = "nl",
    translation_mode: str = "none",
    model_name: str = "",
    prompt_version: str = PROMPT_VERSION,
) -> dict[str, Any] | None:
    from backend.app.core.redis_json import redis_get_json

    key = _cache_key(
        level=level,
        interest_area=interest_area,
        word_count=word_count,
        source_mode=source_mode,
        strictness=strictness,
        source_title=source_title,
        source_url=source_url,
        source_published_at=source_published_at,
        source_content=source_content,
        language=language,
        translation_mode=translation_mode,
        model_name=model_name,
        prompt_version=prompt_version,
    )
    try:
        cached = await redis_get_json(key)
    except Exception as exc:
        logger.warning("reading_generate_cache_get_failed key=%s error=%s", key, exc)
        return None
    return cached if isinstance(cached, dict) else None


async def set_cached_reading_generate(
    *,
    level: int,
    interest_area: str,
    word_count: int,
    source_mode: str,
    strictness: str,
    source_title: str,
    payload: dict[str, Any],
    source_url: str = "",
    source_published_at: str = "",
    source_content: str = "",
    language: str = "nl",
    translation_mode: str = "none",
    model_name: str = "",
    prompt_version: str = PROMPT_VERSION,
    ttl_seconds: int | None = None,
) -> None:
    from backend.app.core.redis_json import redis_set_json

    key = _cache_key(
        level=level,
        interest_area=interest_area,
        word_count=word_count,
        source_mode=source_mode,
        strictness=strictness,
        source_title=source_title,
        source_url=source_url,
        source_published_at=source_published_at,
        source_content=source_content,
        language=language,
        translation_mode=translation_mode,
        model_name=model_name,
        prompt_version=prompt_version,
    )
    try:
        if ttl_seconds is None:
            from backend.app.core.config import settings

            ttl_seconds = settings.READING_GENERATE_CACHE_TTL_SECONDS
        await redis_set_json(key, payload, ttl_seconds=ttl_seconds)
    except Exception as exc:
        logger.warning("reading_generate_cache_set_failed key=%s error=%s", key, exc)
