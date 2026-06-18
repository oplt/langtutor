"""FastAPI dependency providers for application services (testable via dependency_overrides)."""

from __future__ import annotations

from backend.app.modules.agent.runtime.orchestrator import AgentOrchestrator
from backend.app.modules.agent.runtime.registry import ToolRegistry, get_tool_registry
from backend.app.modules.agent.service import get_orchestrator
from backend.app.modules.knowledge.service import KnowledgeService, get_knowledge_service
from backend.app.modules.learning.quiz.application.service import QuizService, get_quiz_service
from backend.app.modules.memory.service import MemoryService, get_memory_service
from backend.app.modules.rag.application.document_ingestion_service import (
    DocumentIngestionService,
    get_document_ingestion_service,
)
from backend.app.modules.tutor.application.tutor_turn_service import (
    TutorTurnService,
    get_tutor_turn_service,
)


def knowledge_service_dep() -> KnowledgeService:
    return get_knowledge_service()


def memory_service_dep() -> MemoryService:
    return get_memory_service()


def tool_registry_dep() -> ToolRegistry:
    return get_tool_registry()


def agent_orchestrator_dep() -> AgentOrchestrator:
    return get_orchestrator()


def tutor_turn_service_dep() -> TutorTurnService:
    return get_tutor_turn_service()


def quiz_service_dep() -> QuizService:
    return get_quiz_service()


def document_ingestion_dep() -> DocumentIngestionService:
    return get_document_ingestion_service()
