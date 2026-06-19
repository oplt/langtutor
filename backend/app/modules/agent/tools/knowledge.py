from __future__ import annotations

from typing import Any

from backend.app.modules.agent.core.context import AgentContext
from backend.app.modules.agent.core.protocols import BaseTool, ToolResult
from backend.app.modules.agent.db_session import get_bound_db_session, resolve_agent_db
from backend.app.modules.knowledge.service import get_knowledge_service

_DEFAULT_KNOWLEDGE_MIN_SCORE = 0.0  # service applies BM25/FTS-specific floor


class SearchKnowledgeTool(BaseTool):
    name = "search_knowledge"
    description = (
        "Search the Dutch knowledge base (word corpus + grammar references) and return "
        "the most relevant grounded snippets. Use this before answering questions "
        "about Dutch word meanings, grammar rules, conjugations, or usage examples."
    )

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query."},
                "kb_name": {
                    "type": "string",
                    "description": "Knowledge base name (default: dutch-core).",
                },
                "top_k": {"type": "integer", "description": "Number of results (1-10)."},
            },
            "required": ["query"],
        }

    async def execute(self, context: AgentContext, **kwargs: Any) -> ToolResult:
        query = str(kwargs.get("query") or "").strip()
        kb_name = str(kwargs.get("kb_name") or "dutch-core").strip() or "dutch-core"
        top_k = int(kwargs.get("top_k") or 5)
        top_k = max(1, min(top_k, 10))

        if not query:
            return ToolResult(content="search_knowledge: query is empty")

        async with resolve_agent_db(context) as db:
            service = get_knowledge_service()
            hits = await service.search(
                db,
                kb_name=kb_name,
                query=query,
                top_k=top_k,
                cefr_level=context.cefr_level,
                min_score=_DEFAULT_KNOWLEDGE_MIN_SCORE,
            )
            if get_bound_db_session(context) is None:
                await db.commit()

        if not hits:
            return ToolResult(
                content=(
                    "No knowledge base matches found above the confidence threshold. "
                    "Tell the learner the answer is uncertain unless they provide more context."
                )
            )

        lines = []
        for idx, hit in enumerate(hits, start=1):
            meta = hit.chunk.metadata_json or {}
            meta_bits = []
            if meta.get("rank"):
                meta_bits.append(f"rank {meta['rank']}")
            if meta.get("pos"):
                meta_bits.append(str(meta["pos"]))
            meta_str = f" ({', '.join(meta_bits)})" if meta_bits else ""
            lines.append(
                f"[{idx}] {hit.chunk.title}{meta_str} — score {hit.score:.2f}\n{hit.chunk.content}"
            )

        return ToolResult(
            content="\n\n".join(lines),
            metadata={
                "kb_name": kb_name,
                "count": len(hits),
                "sources": [
                    {
                        "id": str(hit.chunk.id),
                        "title": hit.chunk.title,
                        "source": hit.chunk.source,
                        "score": hit.score,
                    }
                    for hit in hits
                ],
            },
        )

