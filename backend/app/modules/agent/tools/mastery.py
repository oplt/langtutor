from __future__ import annotations

import uuid
from typing import Any

from backend.app.modules.agent.core.context import AgentContext
from backend.app.modules.agent.core.protocols import BaseTool, ToolResult
from backend.app.modules.agent.db_session import get_bound_db_session, resolve_agent_db


def _parse_level(raw: str | None, context: AgentContext):
    from backend.app.db.base import CEFRLevel

    level_raw = str(raw or context.cefr_level or "A1").upper()
    try:
        return CEFRLevel(level_raw)
    except ValueError:
        return CEFRLevel.A1


def _parse_user_id(context: AgentContext) -> uuid.UUID:
    return uuid.UUID(str(context.user_id))


class MasteryStatusTool(BaseTool):
    name = "mastery_status"
    description = "Read the learner's mastery path map and next objective for their CEFR level."

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "level": {
                    "type": "string",
                    "description": "CEFR level (A1-C2). Defaults to learner context.",
                }
            },
        }

    async def execute(self, context: AgentContext, **kwargs: Any) -> ToolResult:
        from backend.app.modules.learning.mastery.runtime import get_mastery_runtime

        if not context.user_id:
            return ToolResult(content="No authenticated user for mastery status.")
        level = _parse_level(kwargs.get("level"), context)
        async with resolve_agent_db(context) as db:
            payload = await get_mastery_runtime().get_map(
                db, user_id=_parse_user_id(context), level=level
            )
            if get_bound_db_session(context) is None:
                await db.commit()
        nxt = payload["next"]
        return ToolResult(
            content=(
                f"Next: {nxt['action']} — {nxt.get('knowledge_point_name', '')} "
                f"({nxt.get('stage', '')})"
            ),
            metadata={"mastery": payload},
        )


class MasteryGradeTool(BaseTool):
    name = "mastery_grade"
    description = "Grade the learner's answer to the pending mastery quiz question."

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "answer": {"type": "string", "description": "Learner answer text."},
                "level": {"type": "string"},
            },
            "required": ["answer"],
        }

    async def execute(self, context: AgentContext, **kwargs: Any) -> ToolResult:
        from backend.app.modules.learning.mastery.runtime import get_mastery_runtime

        answer = str(kwargs.get("answer") or context.user_message or "").strip()
        if not context.user_id:
            return ToolResult(content="No authenticated user.")
        level = _parse_level(kwargs.get("level"), context)
        async with resolve_agent_db(context) as db:
            result = await get_mastery_runtime().grade_answer(
                db,
                user_id=_parse_user_id(context),
                level=level,
                user_answer=answer,
            )
            if get_bound_db_session(context) is None:
                await db.commit()
        status = "correct" if result["correct"] else "incorrect"
        next_step = result.get("map", {}).get("next") or result.get("next", {})
        return ToolResult(
            content=f"Answer {status}. Next action: {next_step.get('action', '')}",
            metadata=result,
        )
