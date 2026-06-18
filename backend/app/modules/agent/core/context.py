from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentContext:
    """Single-turn payload for capabilities and tools."""

    session_id: str = ""
    user_id: str = ""
    user_message: str = ""
    conversation_history: list[dict[str, Any]] = field(default_factory=list)
    enabled_tools: list[str] | None = None
    active_capability: str | None = None
    language: str = "en"
    cefr_level: str | None = None
    system_prompt: str = ""
    config_overrides: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
