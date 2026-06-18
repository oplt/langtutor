from __future__ import annotations

import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.app.modules.auth.ws import WS_AUTH_FAILED, ws_require_user
from backend.app.modules.auth.ws_tokens import ws_accept_subprotocol
from backend.app.modules.rag.domain.enums import IngestionJobStatus
from backend.app.modules.rag.infrastructure.repositories import get_rag_repository
from backend.app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rag", tags=["rag-ws"])

_TERMINAL_JOB_STATUSES = {
    IngestionJobStatus.COMPLETED.value,
    IngestionJobStatus.FAILED.value,
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
        while True:
            async with AsyncSessionLocal() as db:
                row = await repo.get_job(db, job_uuid)
                if row is None or str(row.user_id) != str(user.id):
                    await ws.send_text(json.dumps({"type": "error", "message": "Job not found"}))
                    break

                document = await repo.get_document(db, document_id=row.document_id)
                progress_stage = document.status if document is not None else None
                payload = {
                    "type": "job_progress",
                    "job_id": job_id,
                    "status": row.status,
                    "progress_stage": progress_stage,
                    "error_message": row.error_message,
                }
                await ws.send_text(json.dumps(payload, default=str))

                if row.status in _TERMINAL_JOB_STATUSES:
                    break

            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        return
    except Exception:
        logger.exception("rag_job_ws_failed job_id=%s", job_id)
        try:
            await ws.send_text(json.dumps({"type": "error", "message": "Unexpected websocket error."}))
        except Exception:
            pass
