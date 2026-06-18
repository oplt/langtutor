from __future__ import annotations

import uuid
from typing import Any

from backend.app.modules.agent.core.context import AgentContext
from backend.app.modules.agent.core.protocols import BaseTool, ToolResult
from backend.app.modules.agent.db_session import get_bound_db_session, resolve_agent_db
from backend.app.modules.notebook.service import get_notebook_service


def _user_uuid(context: AgentContext) -> uuid.UUID:
    return uuid.UUID(str(context.user_id))


class SaveToNotebookTool(BaseTool):
    name = "save_to_notebook"
    description = (
        "Save a Dutch word to the learner's personal vocabulary notebook and queue it "
        "for spaced review. Use when the learner asks to save a word, or when you "
        "introduce an important new word they should study."
    )

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "lemma": {
                    "type": "string",
                    "description": "Dutch word or short phrase to save.",
                },
                "note": {
                    "type": "string",
                    "description": "Short learner-facing note (meaning, tip).",
                },
                "context": {
                    "type": "string",
                    "description": "Sentence or chat snippet where the word appeared.",
                },
            },
            "required": ["lemma"],
        }

    async def execute(self, context: AgentContext, **kwargs: Any) -> ToolResult:
        if not context.user_id:
            return ToolResult(content="Cannot save words without an authenticated user.")

        lemma = str(kwargs.get("lemma") or "").strip()
        if not lemma:
            return ToolResult(content="save_to_notebook: lemma is required")

        note = str(kwargs.get("note") or "").strip()
        chat_context = str(kwargs.get("context") or context.user_message or "").strip()

        async with resolve_agent_db(context) as db:
            service = get_notebook_service()
            entry = await service.save_entry(
                db,
                user_id=_user_uuid(context),
                lemma=lemma,
                note=note,
                context=chat_context[:500],
                source="tutor_chat",
                session_id=context.session_id or None,
                metadata={"turn_id": str(context.metadata.get("turn_id") or "")},
            )
            if get_bound_db_session(context) is None:
                await db.commit()

        linked = "linked to corpus" if entry.word_id else "saved (not in corpus yet)"
        return ToolResult(
            content=f"Saved '{entry.lemma}' to your word bank ({linked}).",
            metadata={"entry_id": str(entry.id), "lemma": entry.lemma, "word_id": str(entry.word_id or "")},
        )
