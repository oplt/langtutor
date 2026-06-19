"""Shared tutor turn orchestration for HTTP and WebSocket entry points."""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import uuid4

from backend.app.modules.agent.core.context import AgentContext
from backend.app.modules.agent.db_session import bind_turn_db_session, clear_turn_db_session
from backend.app.modules.agent.runtime.orchestrator import AgentOrchestrator
from backend.app.modules.tutor.context_factory import build_agent_context
from backend.app.modules.tutor.persistence import finalize_tutor_turn_lifecycle
from backend.app.modules.tutor.schemas import TutorMessageIn, TutorMessageOut
from backend.app.modules.tutor.turn_executor import (
    TutorTurnResult,
    collect_orchestrator_turn,
    iter_orchestrator_turn_frames,
)


async def run_tutor_turn_with_session(
    payload: TutorMessageIn,
    *,
    user_id: str,
    orchestrator: AgentOrchestrator,
    session_id: str | None = None,
    turn_id: str | None = None,
) -> tuple[AgentContext, TutorTurnResult]:
    """Run one tutor turn inside a single DB session owned by this coordinator."""
    from backend.app.db.session import AsyncSessionLocal

    context = build_agent_context(
        payload,
        user_id=user_id,
        session_id=session_id or payload.session_id or str(uuid4()),
        turn_id=turn_id,
    )
    async with AsyncSessionLocal() as db:
        bind_turn_db_session(context, db)
        try:
            result = await collect_orchestrator_turn(orchestrator, context)
            await db.commit()
        except Exception:
            await db.rollback()
            raise
        finally:
            clear_turn_db_session(context)
    return context, result


async def stream_tutor_turn_http(
    payload: TutorMessageIn,
    *,
    user_id: str,
    orchestrator: AgentOrchestrator,
) -> AsyncIterator[dict]:
    """Stream one tutor turn as HTTP/SSE frames, then persist lifecycle state."""
    from backend.app.db.session import AsyncSessionLocal

    session_id = payload.session_id or str(uuid4())
    turn_id = str(uuid4())
    context = build_agent_context(
        payload,
        user_id=user_id,
        session_id=session_id,
        turn_id=turn_id,
    )
    result = TutorTurnResult(reply="")
    async with AsyncSessionLocal() as db:
        bind_turn_db_session(context, db)
        try:
            async for frame in iter_orchestrator_turn_frames(
                orchestrator,
                context,
                session_id=session_id,
                turn_id=turn_id,
            ):
                if frame.get("type") == "event":
                    event = frame.get("event") or {}
                    result.events.append(event)
                    if event.get("type") in {"content", "content_delta"} and event.get("content"):
                        result.reply += str(event["content"])
                    if event.get("type") == "ask_user":
                        result.paused = True
                        result.pause_question = str(event.get("content") or "")
                if frame.get("type") == "turn_paused":
                    result.paused = True
                    result.pause_question = str(frame.get("question") or result.pause_question)
                yield frame
            await db.commit()
        except Exception:
            await db.rollback()
            raise
        finally:
            clear_turn_db_session(context)

    if not result.reply and result.pause_question:
        result.reply = result.pause_question

    await finalize_tutor_turn_from_result(
        context=context,
        payload=payload,
        result=result,
        user_id=user_id,
    )
    yield {
        "type": "result",
        "payload": tutor_message_out_from_result(context, result).model_dump(),
    }


async def finalize_tutor_turn_from_result(
    *,
    context: AgentContext,
    payload: TutorMessageIn,
    result: TutorTurnResult,
    user_id: str,
) -> None:
    turn_id = str(context.metadata.get("turn_id") or "")
    persona = str(context.metadata.get("persona") or "") or None
    status = "paused" if result.paused else "completed"
    await finalize_tutor_turn_lifecycle(
        context=context,
        user_id=user_id,
        turn_id=turn_id,
        session_id=context.session_id,
        capability=context.active_capability or "chat",
        language=context.language,
        cefr_level=context.cefr_level,
        persona=persona,
        user_message=context.user_message,
        conversation_history=payload.conversation_history,
        seq=max(1, len(result.events)),
        status=status,
        events_fragment=result.events,
        assistant_reply_fragment=result.reply,
        paused=result.paused,
        pause_question=result.pause_question or None,
    )


def tutor_message_out_from_result(
    context: AgentContext,
    result: TutorTurnResult,
) -> TutorMessageOut:
    return TutorMessageOut(
        session_id=context.session_id,
        capability=context.active_capability or "chat",
        reply=result.reply,
        paused=result.paused,
        pause_question=result.pause_question,
        events=result.events,
    )
