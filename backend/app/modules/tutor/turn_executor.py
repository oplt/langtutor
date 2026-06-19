"""Collect orchestrator events into a synchronous HTTP-friendly result."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from backend.app.modules.agent.core.context import AgentContext
from backend.app.modules.agent.core.stream import StreamEvent, StreamEventType
from backend.app.modules.agent.runtime.orchestrator import AgentOrchestrator

EventHandler = Callable[[StreamEvent], Awaitable[None]]


@dataclass
class TutorTurnResult:
    reply: str
    paused: bool = False
    pause_question: str = ""
    events: list[dict[str, Any]] = field(default_factory=list)


async def iter_orchestrator_events(
    orchestrator: AgentOrchestrator,
    context: AgentContext,
) -> AsyncIterator[StreamEvent]:
    async for event in orchestrator.handle(context):
        yield event


def _event_dict(event: StreamEvent) -> dict[str, Any]:
    return {
        "type": event.type.value,
        "source": event.source,
        "content": event.content,
        "metadata": event.metadata,
    }


def _accumulate_event(
    event: StreamEvent,
    *,
    events: list[dict[str, Any]],
    reply_parts: list[str],
) -> tuple[bool, str]:
    events.append(_event_dict(event))
    paused = False
    pause_question = ""
    if event.type in {StreamEventType.CONTENT, StreamEventType.CONTENT_DELTA} and event.content:
        reply_parts.append(event.content)
    if event.type == StreamEventType.ASK_USER:
        paused = True
        pause_question = event.content
    return paused, pause_question


async def collect_orchestrator_turn(
    orchestrator: AgentOrchestrator,
    context: AgentContext,
    *,
    on_event: EventHandler | None = None,
) -> TutorTurnResult:
    events: list[dict[str, Any]] = []
    reply_parts: list[str] = []
    paused = False
    pause_question = ""

    async for event in iter_orchestrator_events(orchestrator, context):
        if on_event is not None:
            await on_event(event)
        event_paused, event_pause_question = _accumulate_event(
            event,
            events=events,
            reply_parts=reply_parts,
        )
        if event_paused:
            paused = True
            pause_question = event_pause_question

    reply = "".join(reply_parts) if reply_parts else pause_question
    return TutorTurnResult(
        reply=reply,
        paused=paused,
        pause_question=pause_question,
        events=events,
    )


async def iter_orchestrator_turn_frames(
    orchestrator: AgentOrchestrator,
    context: AgentContext,
    *,
    session_id: str,
    turn_id: str,
) -> AsyncIterator[dict[str, Any]]:
    """Yield HTTP/SSE-friendly frames while a tutor turn runs."""
    seq = 0
    yield {
        "type": "turn_started",
        "turn_id": turn_id,
        "session_id": session_id,
    }

    async for event in iter_orchestrator_events(orchestrator, context):
        seq += 1
        yield {
            "type": "event",
            "turn_id": turn_id,
            "session_id": session_id,
            "seq": seq,
            "event": _event_dict(event),
        }
        if event.type == StreamEventType.ASK_USER:
            meta = event.metadata or {}
            payload: dict[str, Any] = {
                "type": "turn_paused",
                "turn_id": turn_id,
                "session_id": session_id,
                "question": event.content,
            }
            ask_user = meta.get("ask_user")
            if ask_user:
                payload["ask_user"] = ask_user
            yield payload
            return

    yield {
        "type": "turn_done",
        "turn_id": turn_id,
        "session_id": session_id,
    }
