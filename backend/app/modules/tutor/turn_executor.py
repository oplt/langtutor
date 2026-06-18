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
        events.append(
            {
                "type": event.type.value,
                "source": event.source,
                "content": event.content,
                "metadata": event.metadata,
            }
        )
        if event.type in {StreamEventType.CONTENT, StreamEventType.CONTENT_DELTA} and event.content:
            reply_parts.append(event.content)
        if event.type == StreamEventType.ASK_USER:
            paused = True
            pause_question = event.content

    reply = "".join(reply_parts) if reply_parts else pause_question
    return TutorTurnResult(
        reply=reply,
        paused=paused,
        pause_question=pause_question,
        events=events,
    )
