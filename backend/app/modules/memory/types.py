from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

L2_SURFACES = ("chat", "quiz", "story", "practice", "tutor")
L3_SLOTS = ("recent", "profile", "scope", "preferences")

MAX_ENTRY_CHARS = 240
MAX_L2_ENTRIES = 80
MAX_TRACE_FETCH = 200
MAX_TRACE_STORE = 2000

CAPABILITY_L3_SLOT_ORDER: dict[str, tuple[str, ...]] = {
    "mastery_path": ("scope", "recent", "profile", "preferences"),
    "deep_research": ("scope", "recent", "profile", "preferences"),
    "chat": ("recent", "profile", "preferences", "scope"),
    "tutor_chat": ("recent", "profile", "preferences", "scope"),
}


@dataclass
class MemoryEntry:
    id: str
    text: str
    created_at: str
    source: str = ""
    ref: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "created_at": self.created_at,
            "source": self.source,
            "ref": self.ref,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> MemoryEntry:
        return cls(
            id=str(raw.get("id") or f"m_{uuid4().hex[:12]}"),
            text=str(raw.get("text") or ""),
            created_at=str(raw.get("created_at") or _now_iso()),
            source=str(raw.get("source") or ""),
            ref=str(raw.get("ref") or ""),
        )


@dataclass
class TraceEvent:
    surface: str
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)
    session_id: str = ""
    turn_id: str = ""

    def to_row_kwargs(self, user_id) -> dict[str, Any]:
        return {
            "user_id": user_id,
            "surface": self.surface,
            "kind": self.kind,
            "session_id": self.session_id or None,
            "turn_id": self.turn_id or None,
            "payload": self.payload,
        }


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
