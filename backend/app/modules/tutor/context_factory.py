"""Shared tutor → AgentContext construction for HTTP and WebSocket entry points."""

from __future__ import annotations

from uuid import uuid4

from backend.app.core.logging import get_log_context
from backend.app.modules.agent.core.context import AgentContext
from backend.app.modules.tutor.schemas import TutorMessageIn
from backend.app.modules.extensions.auto_router.service import resolve_capability


def build_agent_context(
    payload: TutorMessageIn,
    *,
    user_id: str,
    turn_id: str | None = None,
    session_id: str | None = None,
) -> AgentContext:
    resolved_capability = payload.capability
    route_metadata: dict[str, object] = {}
    if payload.capability in {None, "", "auto"}:
        resolved_capability, route_metadata = resolve_capability(
            payload.capability, payload.message.strip()
        )

    persona = payload.persona
    suggested_persona = route_metadata.get("suggested_persona")
    if (not persona) and isinstance(suggested_persona, str) and suggested_persona:
        persona = suggested_persona

    sid = session_id or payload.session_id or str(uuid4())
    tid = turn_id or str(uuid4())
    log_ctx = get_log_context()
    metadata: dict[str, object] = {
        "turn_id": tid,
        "ui_language": payload.language,
        "persona": persona,
        **route_metadata,
    }
    if log_ctx.get("request_id"):
        metadata["request_id"] = log_ctx["request_id"]
    if log_ctx.get("trace_id"):
        metadata["trace_id"] = log_ctx["trace_id"]

    if payload.cefr_level:
        from backend.app.db.base import CEFRLevel

        try:
            CEFRLevel(str(payload.cefr_level).upper())
        except ValueError:
            metadata["cefr_level_invalid"] = payload.cefr_level

    return AgentContext(
        session_id=sid,
        user_id=user_id,
        user_message=payload.message.strip(),
        conversation_history=payload.conversation_history,
        enabled_tools=payload.enabled_tools,
        active_capability=resolved_capability or "chat",
        language=payload.language,
        cefr_level=payload.cefr_level,
        metadata=metadata,
    )
