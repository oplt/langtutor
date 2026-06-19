from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from backend.app.modules.agent.core.stream import StreamEvent
from backend.app.modules.tutor.turn_models import TurnRecord

EventSender = Callable[[dict[str, Any]], Awaitable[None]]


def build_event_envelope(record: TurnRecord, event: StreamEvent) -> dict[str, Any]:
    return {
        "type": "event",
        "turn_id": record.turn_id,
        "session_id": record.session_id,
        "seq": record.seq,
        "event": {
            "type": event.type.value,
            "source": event.source,
            "content": event.content,
            "metadata": event.metadata,
        },
    }
