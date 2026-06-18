from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AISettingsSection(BaseModel):
    active_provider: str = "ollama"
    system_prompt: str = (
        "You are a supportive Dutch language tutor. Explain clearly, correct gently, "
        "and adapt to the learner's CEFR level."
    )
    providers: dict[str, dict[str, Any]] = Field(default_factory=dict)
    task_defaults: dict[str, dict[str, str]] = Field(default_factory=dict)
    profiles: list[dict[str, Any]] = Field(default_factory=list)
    default_profile_id: str = ""
    task_overrides: dict[str, str] = Field(default_factory=dict)


class SettingsDoc(BaseModel):
    ai: AISettingsSection = Field(default_factory=AISettingsSection)
    updated_at: str | None = None
