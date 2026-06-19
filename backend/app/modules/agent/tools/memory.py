from __future__ import annotations

import uuid
from typing import Any

from backend.app.modules.memory.l3_cache import L3_MEMORY_BLOCK_KEY
from backend.app.modules.agent.core.context import AgentContext
from backend.app.modules.agent.core.protocols import BaseTool, ToolResult
from backend.app.modules.agent.db_session import get_bound_db_session, resolve_agent_db
from backend.app.modules.memory.service import get_memory_service
from backend.app.modules.memory.tasks import enqueue_synthesize_l3
from backend.app.modules.memory.types import TraceEvent


def _user_uuid(context: AgentContext) -> uuid.UUID:
    return uuid.UUID(str(context.user_id))


class ReadMemoryTool(BaseTool):
    name = "read_memory"
    description = (
        "Read the learner's persistent memory: recent activity, profile, scope, "
        "and stated preferences. Use to personalize tutoring — not on every turn."
    )

    def parameters(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    async def execute(self, context: AgentContext, **kwargs: Any) -> ToolResult:
        if not context.user_id:
            return ToolResult(content="No learner memory available (not signed in).")

        preloaded = context.metadata.get(L3_MEMORY_BLOCK_KEY)
        if isinstance(preloaded, str) and preloaded.strip():
            return ToolResult(
                content=preloaded.strip(),
                metadata={"char_count": len(preloaded.strip()), "source": "turn_cache"},
            )

        async with resolve_agent_db(context) as db:
            from backend.app.modules.memory.context_loader import load_l3_memory_block

            text = await load_l3_memory_block(
                db,
                user_id=_user_uuid(context),
                metadata=context.metadata,
                query=context.user_message,
            )
            if get_bound_db_session(context) is None:
                await db.commit()
        if not text.strip():
            await enqueue_synthesize_l3(_user_uuid(context))
            return ToolResult(content="Memory is empty for this learner.")
        return ToolResult(content=text, metadata={"char_count": len(text)})


class WriteMemoryTool(BaseTool):
    name = "write_memory"
    description = (
        "Save an explicit learner preference (tone, language, depth, format) to "
        "long-term memory. Use ONLY when the learner clearly states a preference."
    )

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Preference in the learner's words (max 240 chars).",
                },
                "op": {
                    "type": "string",
                    "enum": ["add", "edit"],
                    "description": "add or edit an existing preference entry",
                },
                "target_id": {
                    "type": "string",
                    "description": "Entry id for edit (m_xxx).",
                },
            },
            "required": ["text"],
        }

    async def execute(self, context: AgentContext, **kwargs: Any) -> ToolResult:
        if not context.user_id:
            return ToolResult(content="Cannot save memory without an authenticated user.")
        text = str(kwargs.get("text") or "").strip()
        op = str(kwargs.get("op") or "add")
        target_id = str(kwargs.get("target_id") or "")
        async with resolve_agent_db(context) as db:
            service = get_memory_service()
            try:
                entry = await service.write_preference(
                    db,
                    user_id=_user_uuid(context),
                    text=text,
                    op=op,
                    target_id=target_id,
                )
                await service.emit(
                    db,
                    user_id=_user_uuid(context),
                    event=TraceEvent(
                        surface="chat",
                        kind="preference",
                        payload={"text": text, "op": op},
                        session_id=context.session_id,
                        turn_id=str(context.metadata.get("turn_id") or ""),
                    ),
                    promote_l2=False,
                )
                if get_bound_db_session(context) is None:
                    await db.commit()
            except ValueError as exc:
                return ToolResult(content=f"Could not save preference: {exc}")
        context.metadata.pop(L3_MEMORY_BLOCK_KEY, None)
        return ToolResult(
            content=f"Saved preference: {entry.text}",
            metadata={"entry": entry.to_dict()},
        )
