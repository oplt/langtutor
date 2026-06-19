from __future__ import annotations

import uuid
from typing import Any

from backend.app.modules.tutor.persistence import persist_tutor_turn
from backend.app.modules.tutor.turn_models import TurnRecord


async def persist_turn_fragment(
    *,
    record: TurnRecord,
    events_fragment: list[dict[str, Any]],
    assistant_reply_fragment: str,
    status: str,
    paused: bool,
    pause_question: str | None,
) -> None:
    await persist_tutor_turn(
        user_id=uuid.UUID(str(record.user_id)),
        turn_id=record.turn_id,
        session_id=record.session_id,
        capability=record.capability,
        language=record.language,
        cefr_level=record.cefr_level,
        persona=record.persona,
        user_message=record.user_message,
        conversation_history=record.conversation_history,
        seq=record.seq,
        status=status,
        events_fragment=events_fragment,
        assistant_reply_fragment=assistant_reply_fragment,
        paused=paused,
        pause_question=pause_question,
    )
