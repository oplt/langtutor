from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StreamEventType(str, Enum):
    SESSION = "session"
    CONTENT = "content"
    CONTENT_DELTA = "content_delta"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    ASK_USER = "ask_user"
    ERROR = "error"
    DONE = "done"


@dataclass
class StreamEvent:
    type: StreamEventType
    source: str = ""
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LoopOutcome:
    final_text: str = ""
    iterations: int = 0
    paused: bool = False
    pause_question: str = ""
    completed: bool = False
    messages: list[dict[str, Any]] = field(default_factory=list)
    pending_tool_call: dict[str, str] | None = None
    ask_user: dict[str, Any] | None = None
