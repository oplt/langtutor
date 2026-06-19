from __future__ import annotations

import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.app.modules.auth.ws import WS_AUTH_FAILED, ws_require_user
from backend.app.modules.auth.ws_tokens import ws_accept_subprotocol
from backend.app.modules.rag.application.job_progress_cache import get_rag_job_progress
from backend.app.modules.rag.domain.enums import IngestionJobStatus
from backend.app.modules.rag.infrastructure.repositories import get_rag_repository
from backend.app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rag", tags=["rag-ws"])

_TERMINAL_JOB_STATUSES = {
    IngestionJobStatus.COMPLETED.value,
    IngestionJobStatus.FAILED.value,
}
_POLL_INTERVAL_SECONDS = 0.25


async def _load_job_progress(
    *,
    repo,
    db,
    job_uuid: uuid.UUID,
    job_id: str,
    user_id: uuid.UUID,
) -> dict[str, object] | None:
    cached = await get_rag_job_progress(job_id)
    if cached is not None:
        return {
            "status": cached.get("status"),
            "progress_stage": cached.get("progress_stage"),
            "error_message": cached.get("error_message"),
        }

    row = await repo.get_job(db, job_uuid)
    if row is None or str(row.user_id) != str(user_id):
        return None

    document = await repo.get_document(db, document_id=row.document_id)
    return {
        "status": row.status,
        "progress_stage": document.status if document is not None else None,
        "error_message": row.error_message,
    }


@router.websocket("/jobs/{job_id}/ws")
async def rag_job_progress_websocket(ws: WebSocket, job_id: str) -> None:
    user = await ws_require_user(ws)
    if user is WS_AUTH_FAILED:
        return

    await ws.accept(subprotocol=ws_accept_subprotocol(ws))
    repo = get_rag_repository()
    job_uuid = uuid.UUID(job_id)

    try:
        async with AsyncSessionLocal() as db:
            while True:
                progress = await get_rag_job_progress(job_id)
                if progress is not None:
                    status = progress.get("status")
                    progress_stage = progress.get("progress_stage")
                    error_message = progress.get("error_message")
                else:
                    progress = await _load_job_progress(
                        repo=repo,
                        db=db,
                        job_uuid=job_uuid,
                        job_id=job_id,
                        user_id=user.id,
                    )
                    if progress is None:
                        await ws.send_text(json.dumps({"type": "error", "message": "Job not found"}))
                        break
                    status = progress["status"]
                    progress_stage = progress["progress_stage"]
                    error_message = progress["error_message"]
                    db.expire_all()

                payload = {
                    "type": "job_progress",
                    "job_id": job_id,
                    "status": status,
                    "progress_stage": progress_stage,
                    "error_message": error_message,
                }
                await ws.send_text(json.dumps(payload, default=str))

                if status in _TERMINAL_JOB_STATUSES:
                    break

                await asyncio.sleep(_POLL_INTERVAL_SECONDS)
    except WebSocketDisconnect:
        return
    except Exception:
        logger.exception("rag_job_ws_failed job_id=%s", job_id)
        try:
            await ws.send_text(json.dumps({"type": "error", "message": "Unexpected websocket error."}))
        except Exception:
            logger.warning(
                "rag_job_ws_error_send_failed job_id=%s",
                job_id,
                exc_info=True,
            )
            try:
                await ws.close(code=1011, reason="Unexpected websocket error")
            except Exception:
                logger.debug(
                    "rag_job_ws_close_failed job_id=%s",
                    job_id,
                    exc_info=True,
                )
