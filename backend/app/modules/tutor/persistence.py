"""Tutor turn DB persistence (sessions + memory traces)."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid

from backend.app.core.dead_letter import record_dead_letter
from backend.app.modules.agent.core.context import AgentContext
from backend.app.modules.memory.service import get_memory_service
from backend.app.modules.memory.tasks import enqueue_synthesize_l3
from backend.app.modules.memory.types import TraceEvent
from backend.app.modules.tutor.sessions.service import get_tutor_sessions_service

logger = logging.getLogger(__name__)

_PERSIST_MAX_ATTEMPTS = 3


async def persist_tutor_turn(
    *,
    user_id: uuid.UUID,
    turn_id: str,
    session_id: str,
    capability: str,
    language: str,
    cefr_level: str | None,
    persona: str | None,
    user_message: str,
    conversation_history: list[dict],
    seq: int,
    status: str,
    events_fragment: list[dict],
    assistant_reply_fragment: str,
    paused: bool,
    pause_question: str | None,
) -> None:
    from backend.app.db.session import AsyncSessionLocal

    safe_events = json.loads(json.dumps(events_fragment, ensure_ascii=False, default=str))
    safe_history = json.loads(json.dumps(conversation_history or [], ensure_ascii=False, default=str))

    last_error: Exception | None = None
    for attempt in range(1, _PERSIST_MAX_ATTEMPTS + 1):
        try:
            async with AsyncSessionLocal() as db:
                service = get_tutor_sessions_service()
                await service.get_or_create_session(
                    db,
                    user_id=user_id,
                    session_id=session_id,
                    capability=capability,
                    language=language,
                    cefr_level=cefr_level,
                    persona=persona,
                )
                await service.upsert_turn(
                    db,
                    user_id=user_id,
                    turn_id=turn_id,
                    session_id=session_id,
                    parent_turn_id=None,
                    seq=seq,
                    status=status,
                    capability=capability,
                    language=language,
                    cefr_level=cefr_level,
                    persona=persona,
                    user_message=user_message,
                    conversation_history=safe_history,
                    assistant_reply_fragment=assistant_reply_fragment or "",
                    events_fragment=safe_events,
                    paused=paused,
                    pause_question=pause_question,
                )
                await db.commit()
            return
        except Exception as exc:
            last_error = exc
            logger.warning(
                "persist_tutor_turn_retry turn_id=%s attempt=%s/%s",
                turn_id,
                attempt,
                _PERSIST_MAX_ATTEMPTS,
                exc_info=True,
            )
            if attempt < _PERSIST_MAX_ATTEMPTS:
                await asyncio.sleep(0.25 * attempt)

    logger.exception("Failed to persist tutor turn %s after retries", turn_id)
    await record_dead_letter(
        "tutor_turn_persistence",
        {
            "turn_id": turn_id,
            "session_id": session_id,
            "user_id": str(user_id),
            "status": status,
            "error_type": last_error.__class__.__name__ if last_error else "Unknown",
            "error": str(last_error) if last_error else "",
        },
    )


async def record_chat_memory(context: AgentContext, *, user_id: str, session_id: str, turn_id: str) -> None:
    from backend.app.db.session import AsyncSessionLocal

    user_uuid = uuid.UUID(str(user_id))
    last_memory_error: Exception | None = None
    for attempt in range(1, _PERSIST_MAX_ATTEMPTS + 1):
        try:
            async with AsyncSessionLocal() as db:
                await get_memory_service().emit(
                    db,
                    user_id=user_uuid,
                    event=TraceEvent(
                        surface="chat",
                        kind="turn_complete",
                        session_id=session_id,
                        turn_id=turn_id,
                        payload={
                            "user_message": context.user_message,
                            "cefr_level": context.cefr_level,
                            "capability": context.active_capability,
                        },
                    ),
                )
                await db.commit()
            await enqueue_synthesize_l3(user_uuid)
            return
        except Exception as exc:
            last_memory_error = exc
            logger.warning(
                "record_chat_memory_retry turn_id=%s attempt=%s/%s",
                turn_id,
                attempt,
                _PERSIST_MAX_ATTEMPTS,
                exc_info=True,
            )
            if attempt < _PERSIST_MAX_ATTEMPTS:
                await asyncio.sleep(0.25 * attempt)

    logger.exception("Failed to record chat memory for turn %s", turn_id)
    await record_dead_letter(
        "chat_memory_persistence",
        {
            "turn_id": turn_id,
            "session_id": session_id,
            "user_id": str(user_id),
            "error_type": last_memory_error.__class__.__name__ if last_memory_error else "Unknown",
            "error": str(last_memory_error) if last_memory_error else "",
        },
    )
