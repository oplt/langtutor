from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.core.config import settings
from backend.app.modules.users.models import User
from backend.app.deps import agent_orchestrator_dep, tutor_turn_service_dep
from backend.app.modules.agent.runtime.orchestrator import AgentOrchestrator
from backend.app.modules.tutor.schemas import TutorMessageIn, TutorMessageOut
from backend.app.modules.auth.dependencies import get_current_user
from backend.app.modules.prompt.manager import AVAILABLE_PACKS
from backend.app.modules.tutor.application.tutor_turn_service import TutorTurnService

router = APIRouter(prefix="/api/tutor", tags=["tutor"])


@router.get("/status")
async def tutor_status(
    user: User = Depends(get_current_user),
    orchestrator: AgentOrchestrator = Depends(agent_orchestrator_dep),
):
    return {
        "status": "ready" if settings.AI_AGENT_ENABLED else "disabled",
        "capabilities": orchestrator.list_capabilities(),
        "tools": orchestrator.list_tools(),
        "prompt_packs": list(AVAILABLE_PACKS),
    }


@router.post("/message", response_model=TutorMessageOut)
async def tutor_message(
    payload: TutorMessageIn,
    user: User = Depends(get_current_user),
    turn_service: TutorTurnService = Depends(tutor_turn_service_dep),
):
    if not settings.AI_AGENT_ENABLED:
        return TutorMessageOut(
            ok=False,
            session_id=payload.session_id or "",
            capability=payload.capability or "tutor_chat",
            reply="AI tutor is disabled in server configuration.",
            events=[],
        )
    return await turn_service.execute_turn(payload, user_id=str(user.id))
