"""TutorTurn use case — shared by HTTP `/api/tutor/message` and WebSocket runtime."""

from __future__ import annotations

from uuid import uuid4

from backend.app.modules.agent.db_session import bind_turn_db_session, clear_turn_db_session
from backend.app.modules.agent.runtime.orchestrator import AgentOrchestrator
from backend.app.modules.tutor.schemas import TutorMessageIn, TutorMessageOut
from backend.app.modules.tutor.context_factory import build_agent_context
from backend.app.modules.tutor.turn_executor import collect_orchestrator_turn


class TutorTurnService:
    def __init__(self, orchestrator: AgentOrchestrator | None = None) -> None:
        self._orchestrator = orchestrator

    def _orchestrator_for_turn(self) -> AgentOrchestrator:
        if self._orchestrator is None:
            from backend.app.modules.agent.service import get_orchestrator

            self._orchestrator = get_orchestrator()
        return self._orchestrator

    async def execute_turn(self, payload: TutorMessageIn, *, user_id: str) -> TutorMessageOut:
        from backend.app.db.session import AsyncSessionLocal

        context = build_agent_context(
            payload, user_id=user_id, session_id=payload.session_id or str(uuid4())
        )
        async with AsyncSessionLocal() as db:
            bind_turn_db_session(context, db)
            try:
                result = await collect_orchestrator_turn(self._orchestrator_for_turn(), context)
                await db.commit()
            except Exception:
                await db.rollback()
                raise
            finally:
                clear_turn_db_session(context)
        return TutorMessageOut(
            session_id=context.session_id,
            capability=context.active_capability or "chat",
            reply=result.reply,
            paused=result.paused,
            pause_question=result.pause_question,
            events=result.events,
        )


_service: TutorTurnService | None = None


def get_tutor_turn_service() -> TutorTurnService:
    global _service
    if _service is None:
        _service = TutorTurnService()
    return _service
