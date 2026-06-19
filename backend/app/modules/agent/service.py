from __future__ import annotations

from backend.app.modules.agent.runtime.orchestrator import AgentOrchestrator

__all__ = [
    "AgentOrchestrator",
    "get_orchestrator",
]

_orchestrator = AgentOrchestrator()


def get_orchestrator() -> AgentOrchestrator:
    return _orchestrator
