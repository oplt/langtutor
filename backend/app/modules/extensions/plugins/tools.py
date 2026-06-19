from __future__ import annotations

from typing import Any

from backend.app.modules.agent.core.context import AgentContext
from backend.app.modules.agent.core.protocols import BaseTool, ToolResult
from backend.app.modules.agent.db_session import get_bound_db_session, resolve_agent_db
from backend.app.modules.extensions.dict_lookup_cache import (
    get_dict_lookup,
    set_dict_lookup,
)


class LookupDictionaryTool(BaseTool):
    name = "lookup_dictionary"
    description = (
        "Look up a Dutch lemma in the learner dictionary plugin. "
        "Returns a short gloss and part of speech when available."
    )

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "lemma": {"type": "string", "description": "Dutch word or phrase to look up."},
            },
            "required": ["lemma"],
        }

    async def execute(self, context: AgentContext, **kwargs: Any) -> ToolResult:
        lemma = str(kwargs.get("lemma") or "").strip()
        if not lemma:
            return ToolResult(content="lookup_dictionary: lemma is empty")

        cached = await get_dict_lookup(lemma)
        if cached is not None:
            return ToolResult(
                content=str(cached["content"]),
                metadata=dict(cached.get("metadata") or {}),
            )

        from sqlalchemy import select

        from backend.app.modules.learning.models import Word

        async with resolve_agent_db(context) as db:
            from backend.app.modules.knowledge.service import get_knowledge_service

            service = get_knowledge_service()
            hits = await service.search(db, kb_name="dutch-core", query=lemma, top_k=3)
            word = (
                await db.execute(
                    select(Word)
                    .where(Word.lemma.ilike(lemma))
                    .order_by(Word.rank.asc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            if get_bound_db_session(context) is None:
                await db.commit()

        if word is not None:
            result = ToolResult(
                content=f"{word.lemma}: CEFR {word.level.value}, frequency rank {word.rank}.",
                metadata={"source": "word_corpus", "word_id": str(word.id), "rank": word.rank},
            )
        elif hits:
            top = hits[0].chunk
            result = ToolResult(
                content=f"{lemma}: {top.content[:400]}",
                metadata={"source": "knowledge_base", "title": top.title},
            )
        else:
            result = ToolResult(
                content=f"No dictionary entry for '{lemma}' in the local Dutch corpus.",
                metadata={"source": "local_corpus"},
            )

        await set_dict_lookup(
            lemma,
            content=result.content,
            metadata=result.metadata or {},
        )
        return result
