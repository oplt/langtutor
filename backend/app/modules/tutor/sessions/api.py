from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from backend.app.modules.users.models import User
from backend.app.db.session import get_db
from backend.app.modules.auth.dependencies import get_current_user
from backend.app.modules.tutor.sessions.schemas import (
    TutorChatSessionOut,
    TutorChatTurnOut,
    TutorTurnReplayOut,
)
from backend.app.modules.tutor.sessions.service import get_tutor_sessions_service


router = APIRouter(prefix="/api/tutor/sessions", tags=["tutor-sessions"])


@router.get("")
async def list_sessions(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    service = get_tutor_sessions_service()
    rows = await service.list_sessions(db, user_id=user.id)
    return {
        "sessions": [
            TutorChatSessionOut(
                session_id=row.session_id,
                capability=row.capability,
                language=row.language,
                cefr_level=row.cefr_level,
                persona=row.persona,
                created_at=row.created_at,
                updated_at=row.updated_at,
                last_turn_at=row.last_turn_at,
            )
            for row in rows
        ]
    }


@router.get("/{session_id}/turns")
async def list_turns(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = get_tutor_sessions_service()
    turns = await service.list_turns(db, user_id=user.id, session_id=session_id)
    return {
        "turns": [
            TutorChatTurnOut(
                turn_id=row.turn_id,
                parent_turn_id=row.parent_turn_id,
                seq=row.seq,
                status=row.status,
                capability=row.capability,
                language=row.language,
                cefr_level=row.cefr_level,
                persona=row.persona,
                user_message=row.user_message,
                paused=bool(row.paused),
                pause_question=row.pause_question,
                assistant_reply=row.assistant_reply,
                conversation_history=row.conversation_history or [],
                events=row.events or [],
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in turns
        ]
    }


@router.get("/{session_id}/turns/{turn_id}/replay")
async def replay_turn(
    session_id: str,
    turn_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = get_tutor_sessions_service()
    turn = await service.get_turn(db, user_id=user.id, turn_id=turn_id)
    if turn is None or turn.session_id != session_id:
        raise HTTPException(status_code=404, detail="turn_not_found")
    reconstructed = await service.reconstruct_conversation_history(
        db, user_id=user.id, turn_id=turn_id
    )
    return TutorTurnReplayOut(
        session_id=session_id,
        turn=TutorChatTurnOut(
            turn_id=turn.turn_id,
            parent_turn_id=turn.parent_turn_id,
            seq=turn.seq,
            status=turn.status,
            capability=turn.capability,
            language=turn.language,
            cefr_level=turn.cefr_level,
            persona=turn.persona,
            user_message=turn.user_message,
            paused=bool(turn.paused),
            pause_question=turn.pause_question,
            assistant_reply=turn.assistant_reply,
            conversation_history=turn.conversation_history or [],
            events=turn.events or [],
            created_at=turn.created_at,
            updated_at=turn.updated_at,
        ),
        reconstructed_conversation_history=reconstructed,
    )

