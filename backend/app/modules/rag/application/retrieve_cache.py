from __future__ import annotations

import hashlib
import logging
from typing import Any

from backend.app.modules.rag.domain.models import RetrievedChunk

logger = logging.getLogger(__name__)

_RETRIEVE_CACHE_TTL_SECONDS = 60
_REDIS_PREFIX = "rag:retrieve:"


def retrieval_policy_revision(
    *,
    is_admin: bool,
    allowed_owner_ids: list[str],
    source_types: list[str] | None,
) -> str:
    owners = ",".join(sorted(allowed_owner_ids))
    sources = ",".join(sorted(source_types or [])) or "_"
    admin = "1" if is_admin else "0"
    digest = hashlib.sha256(f"{admin}:{owners}:{sources}".encode("utf-8")).hexdigest()
    return digest[:12]


def _cache_key(
    *,
    user_id: str,
    project_id: str | None,
    query: str,
    top_k: int,
    document_ids: list[str] | None,
    policy_revision: str,
) -> str:
    normalized = " ".join(query.strip().lower().split())
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    project = project_id or "_"
    docs = ",".join(sorted(document_ids or [])) or "_"
    return f"{_REDIS_PREFIX}{user_id}:{project}:{top_k}:{docs}:{policy_revision}:{digest}"


def _serialize_chunks(chunks: list[RetrievedChunk]) -> list[dict[str, Any]]:
    return [
        {
            "chunk_id": chunk.chunk_id,
            "document_id": chunk.document_id,
            "content": chunk.content,
            "score": chunk.score,
            "metadata": chunk.metadata,
            "filename": chunk.filename,
            "chunk_index": chunk.chunk_index,
            "page_number": chunk.page_number,
        }
        for chunk in chunks
    ]


def _deserialize_chunks(payload: list[dict[str, Any]]) -> list[RetrievedChunk]:
    return [
        RetrievedChunk(
            chunk_id=str(item["chunk_id"]),
            document_id=str(item["document_id"]),
            content=str(item.get("content") or ""),
            score=float(item.get("score") or 0.0),
            metadata=dict(item.get("metadata") or {}),
            filename=str(item.get("filename") or ""),
            chunk_index=int(item.get("chunk_index") or 0),
            page_number=item.get("page_number"),
        )
        for item in payload
    ]


async def get_cached_retrieve(
    *,
    user_id: str,
    project_id: str | None,
    query: str,
    top_k: int,
    document_ids: list[str] | None,
    policy_revision: str,
) -> list[RetrievedChunk] | None:
    from backend.app.core.redis_json import redis_get_json

    key = _cache_key(
        user_id=user_id,
        project_id=project_id,
        query=query,
        top_k=top_k,
        document_ids=document_ids,
        policy_revision=policy_revision,
    )
    cached = await redis_get_json(key)
    if not isinstance(cached, list):
        return None
    try:
        return _deserialize_chunks(cached)
    except (KeyError, TypeError, ValueError):
        logger.debug("rag_retrieve_cache_corrupt key=%s", key)
        return None


async def set_cached_retrieve(
    *,
    user_id: str,
    project_id: str | None,
    query: str,
    top_k: int,
    document_ids: list[str] | None,
    policy_revision: str,
    chunks: list[RetrievedChunk],
) -> None:
    from backend.app.core.redis_json import redis_set_json

    key = _cache_key(
        user_id=user_id,
        project_id=project_id,
        query=query,
        top_k=top_k,
        document_ids=document_ids,
        policy_revision=policy_revision,
    )
    await redis_set_json(
        key,
        _serialize_chunks(chunks),
        ttl_seconds=_RETRIEVE_CACHE_TTL_SECONDS,
    )


async def invalidate_user_retrieve_cache(user_id: str) -> None:
    try:
        from backend.app.core.redis import get_redis

        redis = get_redis()
        pattern = f"{_REDIS_PREFIX}{user_id}:*"
        cursor = 0
        while True:
            cursor, keys = await redis.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                await redis.delete(*keys)
            if cursor == 0:
                break
    except Exception:
        logger.debug("rag_retrieve_cache_invalidate_failed user_id=%s", user_id, exc_info=True)
