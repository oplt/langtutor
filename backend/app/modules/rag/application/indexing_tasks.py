from __future__ import annotations

import logging

from backend.app.core.redis_lock import release_job_lock, try_acquire_job_lock
from backend.app.modules.rag.application.document_ingestion_service import (
    get_document_ingestion_service,
)

logger = logging.getLogger(__name__)

_RAG_INDEX_LOCK_TTL_SECONDS = 7200


def _lock_key(document_id: str) -> str:
    return f"jobs:rag:index:{document_id}"


async def run_rag_index_job(
    *,
    job_id: str,
    user_id: str,
    document_id: str,
    project_id: str | None,
) -> None:
    lock_key = _lock_key(document_id)
    if not await try_acquire_job_lock(lock_key, ttl_seconds=_RAG_INDEX_LOCK_TTL_SECONDS):
        logger.info(
            "rag_index_skipped_duplicate document_id=%s job_id=%s",
            document_id,
            job_id,
        )
        return

    service = get_document_ingestion_service()
    try:
        await service.execute_index_job(
            job_id=job_id,
            user_id=user_id,
            document_id=document_id,
            project_id=project_id,
        )
    except Exception:
        logger.exception(
            "rag_index_background_failed job_id=%s document_id=%s",
            job_id,
            document_id,
        )
    finally:
        await release_job_lock(lock_key)
