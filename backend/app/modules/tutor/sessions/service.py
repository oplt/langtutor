from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.modules.tutor.sessions.models import TutorChatSession, TutorChatTurn


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TutorSessionsService:
    async def get_or_create_session(
        self,
        db: AsyncSession,
        *,
        user_id,
        session_id: str,
        capability: str,
        language: str,
        cefr_level: str | None = None,
        persona: str | None = None,
    ) -> TutorChatSession:
        row = (
            await db.execute(
                select(TutorChatSession).where(TutorChatSession.user_id == user_id).where(
                    TutorChatSession.session_id == session_id
                )
            )
        ).scalar_one_or_none()
        if row is None:
            row = TutorChatSession(
                user_id=user_id,
                session_id=session_id,
                capability=capability or "chat",
                language=language or "en",
                cefr_level=cefr_level,
                persona=persona,
                last_turn_at=_utcnow(),
            )
            db.add(row)
            await db.flush()
        else:
            row.language = language or row.language
            row.capability = capability or row.capability
            row.cefr_level = cefr_level or row.cefr_level
            row.persona = persona or row.persona
            row.last_turn_at = _utcnow()
            await db.flush()
        return row

    async def upsert_turn(
        self,
        db: AsyncSession,
        *,
        user_id,
        turn_id: str,
        session_id: str,
        seq: int,
        status: str,
        capability: str,
        language: str,
        cefr_level: str | None,
        persona: str | None,
        user_message: str,
        conversation_history: list[dict[str, Any]],
        assistant_reply_fragment: str,
        events_fragment: list[dict[str, Any]],
        paused: bool,
        pause_question: str | None,
        parent_turn_id: str | None = None,
    ) -> TutorChatTurn:
        existing = (
            await db.execute(
                select(TutorChatTurn)
                .where(TutorChatTurn.user_id == user_id)
                .where(TutorChatTurn.turn_id == turn_id)
            )
        ).scalar_one_or_none()

        if existing is None:
            row = TutorChatTurn(
                user_id=user_id,
                session_id=session_id,
                turn_id=turn_id,
                parent_turn_id=parent_turn_id,
                seq=seq,
                status=status,
                capability=capability or "chat",
                language=language or "en",
                cefr_level=cefr_level,
                persona=persona,
                user_message=user_message or "",
                conversation_history=conversation_history or [],
                assistant_reply=assistant_reply_fragment or "",
                paused=bool(paused),
                pause_question=pause_question,
                events=events_fragment or [],
            )
            db.add(row)
            await db.flush()
            return row

        # Append fragments for multi-part turns (pause/resume).
        existing.seq = seq
        existing.status = status
        existing.capability = capability or existing.capability
        existing.language = language or existing.language
        existing.cefr_level = cefr_level or existing.cefr_level
        existing.persona = persona or existing.persona
        if user_message and not existing.user_message:
            existing.user_message = user_message
        if conversation_history and not existing.conversation_history:
            existing.conversation_history = conversation_history
        if assistant_reply_fragment:
            existing.assistant_reply = (existing.assistant_reply or "") + assistant_reply_fragment
        if events_fragment:
            existing.events = (existing.events or []) + events_fragment
        existing.paused = bool(paused)
        existing.pause_question = pause_question if paused else None
        existing.parent_turn_id = parent_turn_id or existing.parent_turn_id
        await db.flush()
        return existing

    async def list_sessions(self, db: AsyncSession, *, user_id) -> list[TutorChatSession]:
        rows = (
            await db.execute(
                select(TutorChatSession)
                .where(TutorChatSession.user_id == user_id)
                .order_by(TutorChatSession.last_turn_at.desc().nullslast(), TutorChatSession.updated_at.desc())
            )
        ).scalars().all()
        return list(rows)

    async def list_turns(
        self, db: AsyncSession, *, user_id, session_id: str
    ) -> list[TutorChatTurn]:
        rows = (
            await db.execute(
                select(TutorChatTurn)
                .where(TutorChatTurn.user_id == user_id)
                .where(TutorChatTurn.session_id == session_id)
                .order_by(TutorChatTurn.created_at.asc())
            )
        ).scalars().all()
        return list(rows)

    async def get_turn(self, db: AsyncSession, *, user_id, turn_id: str) -> TutorChatTurn | None:
        return (
            await db.execute(
                select(TutorChatTurn)
                .where(TutorChatTurn.user_id == user_id)
                .where(TutorChatTurn.turn_id == turn_id)
            )
        ).scalar_one_or_none()

    async def reconstruct_conversation_history(
        self, db: AsyncSession, *, user_id, turn_id: str
    ) -> list[dict[str, Any]]:
        turn = await self.get_turn(db, user_id=user_id, turn_id=turn_id)
        if turn is None:
            return []
        out: list[dict[str, Any]] = []
        out.extend(turn.conversation_history or [])
        if turn.user_message:
            out.append({"role": "user", "content": turn.user_message})
        if turn.assistant_reply:
            out.append({"role": "assistant", "content": turn.assistant_reply})
        return out


_service: TutorSessionsService | None = None


def get_tutor_sessions_service() -> TutorSessionsService:
    global _service
    if _service is None:
        _service = TutorSessionsService()
    return _service

