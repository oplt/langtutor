from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class TutorChatSessionOut(BaseModel):
    session_id: str
    capability: str
    language: str
    cefr_level: Optional[str]
    persona: Optional[str]
    created_at: datetime
    updated_at: datetime
    last_turn_at: Optional[datetime] = None


class TutorChatTurnOut(BaseModel):
    turn_id: str
    parent_turn_id: Optional[str]
    seq: int
    status: str
    capability: str
    language: str
    cefr_level: Optional[str]
    persona: Optional[str]
    user_message: str
    paused: bool
    pause_question: Optional[str] = None
    assistant_reply: str
    conversation_history: list[dict[str, Any]] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class TutorTurnReplayOut(BaseModel):
    session_id: str
    turn: TutorChatTurnOut
    reconstructed_conversation_history: list[dict[str, Any]] = Field(default_factory=list)

