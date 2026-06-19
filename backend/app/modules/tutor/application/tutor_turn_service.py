"""TutorTurn use case — shared by HTTP `/api/tutor/message` and WebSocket runtime."""

from __future__ import annotations

from collections.abc import AsyncIterator

from backend.app.modules.agent.runtime.orchestrator import AgentOrchestrator
from backend.app.modules.tutor.application.turn_coordinator import (
    finalize_tutor_turn_from_result,
    run_tutor_turn_with_session,
    stream_tutor_turn_http,
    tutor_message_out_from_result,
)
from backend.app.modules.tutor.schemas import TutorMessageIn, TutorMessageOut


class TutorTurnService:
    def __init__(self, orchestrator: AgentOrchestrator | None = None) -> None:
        self._orchestrator = orchestrator

    def _orchestrator_for_turn(self) -> AgentOrchestrator:
        if self._orchestrator is None:
            from backend.app.modules.agent.service import get_orchestrator

            self._orchestrator = get_orchestrator()
        return self._orchestrator

    async def execute_turn(self, payload: TutorMessageIn, *, user_id: str) -> TutorMessageOut:
        context, result = await run_tutor_turn_with_session(
            payload,
            user_id=user_id,
            orchestrator=self._orchestrator_for_turn(),
        )
        await finalize_tutor_turn_from_result(
            context=context,
            payload=payload,
            result=result,
            user_id=user_id,
        )
        return tutor_message_out_from_result(context, result)

    async def stream_turn(
        self,
        payload: TutorMessageIn,
        *,
        user_id: str,
    ) -> AsyncIterator[dict]:
        async for frame in stream_tutor_turn_http(
            payload,
            user_id=user_id,
            orchestrator=self._orchestrator_for_turn(),
        ):
            yield frame


_service: TutorTurnService | None = None


def get_tutor_turn_service() -> TutorTurnService:
    global _service
    if _service is None:
        _service = TutorTurnService()
    return _service
