from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.app.modules.tutor.turn_state_store import StoredPausedTurnState, StoredTurnRecord


@dataclass
class PausedTurnState:
    session_id: str
    capability: str
    cefr_level: str | None
    persona: str | None
    language: str
    enabled_tools: list[str] | None
    system_prompt: str
    agent_messages: list[dict[str, Any]]
    pause_question: str
    pending_tool_call: dict[str, str] | None = None
    ask_user: dict[str, Any] | None = None


@dataclass
class TurnRecord:
    turn_id: str
    session_id: str
    user_id: str
    status: str = "running"
    seq: int = 0
    task: Any = None
    paused: PausedTurnState | None = None
    user_message: str = ""
    conversation_history: list[dict[str, Any]] = field(default_factory=list)
    capability: str = "chat"
    language: str = "en"
    cefr_level: str | None = None
    persona: str | None = None


def paused_to_stored(state: PausedTurnState) -> StoredPausedTurnState:
    return StoredPausedTurnState(
        session_id=state.session_id,
        capability=state.capability,
        cefr_level=state.cefr_level,
        persona=state.persona,
        language=state.language,
        enabled_tools=state.enabled_tools,
        system_prompt=state.system_prompt,
        agent_messages=state.agent_messages,
        pause_question=state.pause_question,
        pending_tool_call=state.pending_tool_call,
        ask_user=state.ask_user,
    )


def paused_from_stored(state: StoredPausedTurnState) -> PausedTurnState:
    return PausedTurnState(
        session_id=state.session_id,
        capability=state.capability,
        cefr_level=state.cefr_level,
        persona=state.persona,
        language=state.language,
        enabled_tools=state.enabled_tools,
        system_prompt=state.system_prompt,
        agent_messages=state.agent_messages,
        pause_question=state.pause_question,
        pending_tool_call=state.pending_tool_call,
        ask_user=state.ask_user,
    )


def record_to_stored(record: TurnRecord) -> StoredTurnRecord:
    return StoredTurnRecord(
        turn_id=record.turn_id,
        session_id=record.session_id,
        user_id=record.user_id,
        status=record.status,
        seq=record.seq,
        paused=paused_to_stored(record.paused) if record.paused else None,
        user_message=record.user_message,
        conversation_history=record.conversation_history,
        capability=record.capability,
        language=record.language,
        cefr_level=record.cefr_level,
        persona=record.persona,
    )


def record_from_stored(
    stored: StoredTurnRecord,
    *,
    task: Any = None,
) -> TurnRecord:
    return TurnRecord(
        turn_id=stored.turn_id,
        session_id=stored.session_id,
        user_id=stored.user_id,
        status=stored.status,
        seq=stored.seq,
        task=task,
        paused=paused_from_stored(stored.paused) if stored.paused else None,
        user_message=stored.user_message,
        conversation_history=stored.conversation_history,
        capability=stored.capability,
        language=stored.language,
        cefr_level=stored.cefr_level,
        persona=stored.persona,
    )
