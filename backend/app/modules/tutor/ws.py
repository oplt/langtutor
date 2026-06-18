from __future__ import annotations

import json
import logging
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.app.core.config import settings
from backend.app.core.logging import set_log_context
from backend.app.modules.tutor.schemas import TutorMessageIn
from backend.app.modules.auth.ws import WS_AUTH_FAILED, ws_require_user
from backend.app.modules.auth.ws_tokens import ws_accept_subprotocol
from backend.app.modules.tutor.turn_runtime import get_tutor_turn_runtime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tutor", tags=["tutor-ws"])


@router.websocket("/ws")
async def tutor_websocket(ws: WebSocket) -> None:
    user = await ws_require_user(ws)
    if user is WS_AUTH_FAILED:
        return

    await ws.accept(subprotocol=ws_accept_subprotocol(ws))
    closed = False
    runtime = get_tutor_turn_runtime()
    user_id = str(user.id)
    set_log_context(trace_id=str(uuid4()), user_id=user_id)

    async def safe_send(data: dict[str, Any]) -> None:
        nonlocal closed
        if closed:
            return
        try:
            await ws.send_text(json.dumps(data, ensure_ascii=False, default=str))
        except Exception:
            closed = True

    try:
        while not closed:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await safe_send({"type": "error", "message": "Invalid JSON."})
                continue

            msg_type = msg.get("type")
            client_trace = msg.get("trace_id")
            if isinstance(client_trace, str) and client_trace.strip():
                set_log_context(trace_id=client_trace.strip(), user_id=user_id)

            if msg_type == "ping":
                await safe_send({"type": "pong"})
                continue

            if not settings.AI_AGENT_ENABLED:
                await safe_send({"type": "error", "message": "AI tutor is disabled."})
                continue

            if msg_type in {"message", "start_turn"}:
                payload_raw = msg.get("payload") or msg
                try:
                    payload = TutorMessageIn.model_validate(payload_raw)
                except Exception as exc:
                    await safe_send({"type": "error", "message": f"Invalid payload: {exc}"})
                    continue
                try:
                    await runtime.start_turn(payload=payload, user_id=user_id, send=safe_send)
                except RuntimeError as exc:
                    code = str(exc)
                    if code == "turn_busy":
                        await safe_send(
                            {
                                "type": "error",
                                "code": "turn_busy",
                                "message": "A turn is already running for this session.",
                            }
                        )
                    else:
                        await safe_send({"type": "error", "message": code})
                continue

            if msg_type == "submit_user_reply":
                turn_id = str(msg.get("turn_id") or "")
                reply = str(msg.get("reply") or "").strip()
                answers_raw = msg.get("answers")
                answers: list[dict[str, str]] | None = None
                if isinstance(answers_raw, list) and answers_raw:
                    answers = []
                    for entry in answers_raw:
                        if not isinstance(entry, dict):
                            continue
                        qid = str(entry.get("questionId") or entry.get("id") or "").strip()
                        text = str(entry.get("text") or "").strip()
                        if qid and text:
                            answers.append({"questionId": qid, "text": text})
                    if not answers:
                        answers = None
                if not turn_id or (not reply and not answers):
                    await safe_send(
                        {"type": "error", "message": "turn_id and reply or answers are required."}
                    )
                    continue
                try:
                    await runtime.submit_user_reply(
                        turn_id=turn_id,
                        reply=reply,
                        answers=answers,
                        user_id=user_id,
                        send=safe_send,
                    )
                except RuntimeError as exc:
                    await safe_send({"type": "error", "code": str(exc), "message": str(exc)})
                continue

            if msg_type == "cancel_turn":
                turn_id = str(msg.get("turn_id") or "")
                if not turn_id:
                    await safe_send({"type": "error", "message": "turn_id is required."})
                    continue
                try:
                    await runtime.cancel_turn(turn_id, user_id=user_id)
                    await safe_send({"type": "turn_cancelled", "turn_id": turn_id})
                except RuntimeError as exc:
                    await safe_send({"type": "error", "code": str(exc), "message": str(exc)})
                continue

            await safe_send({"type": "error", "message": f"Unsupported message type: {msg_type}"})
    except WebSocketDisconnect:
        closed = True
    except Exception:
        logger.exception("Tutor websocket error for user %s", user_id)
        await safe_send({"type": "error", "message": "Unexpected websocket error."})
