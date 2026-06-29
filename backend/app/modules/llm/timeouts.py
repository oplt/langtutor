"""Task-level LLM timeout resolution."""

from __future__ import annotations

from backend.app.core.config import settings

# Multi-step tutor/agent flows and adjacent long LLM calls share the tutor ceiling.
TUTOR_TIMEOUT_TASKS = frozenset(
    {
        "tutor_chat",
        "chat",
        "memory_synthesis",
        "rag_answer",
    }
)


def apply_task_timeout(task: str, configured_seconds: float) -> float:
    """Apply task-specific timeout ceilings and floors."""
    if task in {"reading_generation", "reading_translation"}:
        return min(float(configured_seconds), float(settings.LLM_TUTOR_TIMEOUT_SECONDS))
    if task in TUTOR_TIMEOUT_TASKS:
        return max(float(configured_seconds), float(settings.LLM_TUTOR_TIMEOUT_SECONDS))
    return float(configured_seconds)
