from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TutorMessageIn(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    session_id: str | None = None
    capability: str | None = "auto"
    cefr_level: str | None = None
    persona: str | None = None
    language: str = "en"
    conversation_history: list[dict[str, Any]] = Field(default_factory=list)
    enabled_tools: list[str] | None = None


class TutorMessageOut(BaseModel):
    ok: bool = True
    session_id: str
    capability: str
    reply: str
    paused: bool = False
    pause_question: str = ""
    events: list[dict[str, Any]] = Field(default_factory=list)
