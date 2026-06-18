from __future__ import annotations

from backend.app.modules.agent.runtime.orchestrator import AgentOrchestrator
from backend.app.modules.tutor.schemas import TutorMessageIn, TutorMessageOut

__all__ = [
    "AgentOrchestrator",
    "TutorMessageIn",
    "TutorMessageOut",
    "get_orchestrator",
    "run_tutor_turn",
]

_orchestrator = AgentOrchestrator()


async def run_tutor_turn(payload: TutorMessageIn, *, user_id: str) -> TutorMessageOut:
    from backend.app.modules.tutor.application.tutor_turn_service import get_tutor_turn_service

    return await get_tutor_turn_service().execute_turn(payload, user_id=user_id)


def get_orchestrator() -> AgentOrchestrator:
    return _orchestrator
