from __future__ import annotations

import hashlib
import logging

from backend.app.core.config import settings
from backend.app.core.redis_json import redis_get_json, redis_set_json

logger = logging.getLogger(__name__)

_CACHE_VERSION = "v1"


def _embedding_cache_key(text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    provider = settings.RAG_EMBEDDING_PROVIDER.lower()
    model = settings.RAG_EMBEDDING_MODEL
    return f"rag:embed:{_CACHE_VERSION}:{provider}:{model}:{digest}"


async def get_cached_embedding(text: str) -> list[float] | None:
    cached = await redis_get_json(_embedding_cache_key(text))
    if not isinstance(cached, list):
        return None
    try:
        return [float(value) for value in cached]
    except (TypeError, ValueError):
        logger.debug("rag_embedding_cache_invalid key=%s", _embedding_cache_key(text))
        return None


async def set_cached_embedding(text: str, vector: list[float]) -> None:
    await redis_set_json(
        _embedding_cache_key(text),
        vector,
        ttl_seconds=settings.RAG_EMBEDDING_CACHE_TTL_SECONDS,
    )
