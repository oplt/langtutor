from __future__ import annotations

from typing import Any

from backend.app.modules.agent.core.context import AgentContext
from backend.app.modules.agent.core.protocols import BaseTool, ToolResult
from backend.app.modules.agent.db_session import get_bound_db_session, resolve_agent_db


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

        from sqlalchemy import select

        from backend.app.modules.learning.models import Word

        async with resolve_agent_db(context) as db:
            from backend.app.modules.agent.db_session import get_bound_db_session
            from backend.app.modules.knowledge.service import get_knowledge_service

            service = get_knowledge_service()
            await service.ensure_default_kb(db)
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
            return ToolResult(
                content=f"{word.lemma}: CEFR {word.level.value}, frequency rank {word.rank}.",
                metadata={"source": "word_corpus", "word_id": str(word.id), "rank": word.rank},
            )

        if hits:
            top = hits[0].chunk
            return ToolResult(
                content=f"{lemma}: {top.content[:400]}",
                metadata={"source": "knowledge_base", "title": top.title},
            )

        return ToolResult(
            content=f"No dictionary entry for '{lemma}' in the local Dutch corpus.",
            metadata={"source": "local_corpus"},
        )


class PronunciationForvoTool(BaseTool):
    name = "pronunciation_forvo"
    description = (
        "Return pronunciation guidance for a Dutch word. "
        "Production deployments should call the Forvo API or TTS service."
    )

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "word": {"type": "string", "description": "Dutch word to pronounce."},
            },
            "required": ["word"],
        }

    async def execute(self, context: AgentContext, **kwargs: Any) -> ToolResult:
        word = str(kwargs.get("word") or "").strip()
        if not word:
            return ToolResult(content="pronunciation_forvo: word is empty")
        guidance = _dutch_pronunciation_hint(word)
        return ToolResult(
            content=f"{word}: {guidance}",
            metadata={"source": "rule_based_pronunciation", "word": word},
        )


def _dutch_pronunciation_hint(word: str) -> str:
    lower = word.lower()
    hints: list[str] = []
    if "ui" in lower:
        hints.append("ui sounds like Dutch /œy/")
    if "ij" in lower or "ei" in lower:
        hints.append("ij/ei sounds like /ɛi/")
    if "oe" in lower:
        hints.append("oe sounds like /u/")
    if "eu" in lower:
        hints.append("eu sounds like /ø/")
    if "sch" in lower:
        hints.append("sch starts with /sx/")
    if lower.startswith("g") or "ch" in lower:
        hints.append("g/ch use a guttural fricative")
    if not hints:
        hints.append("stress is usually on the first syllable unless a prefix is unstressed")
    return "; ".join(hints)
