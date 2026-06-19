from __future__ import annotations

from typing import Any

from backend.app.core.config import settings
from backend.app.modules.agent.core.context import AgentContext
from backend.app.modules.agent.core.protocols import BaseTool, ToolResult
from backend.app.modules.agent.db_session import get_bound_db_session, resolve_agent_db
from backend.app.modules.rag.application.rag_context_builder import RagContextBuilder
from backend.app.modules.rag.application.retrieval_service import RetrievalService
from backend.app.modules.rag.domain.value_objects import AccessContext


class RagSearchTool(BaseTool):
    """Search the user's uploaded/indexed documents (LangChain RAG module)."""

    name = "rag_search"
    description = (
        "Search the learner's uploaded documents for relevant passages. "
        "Use when the question depends on user-provided files, notes, or project materials. "
        "Returns grounded snippets with document and chunk identifiers."
    )

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query."},
                "project_id": {
                    "type": "string",
                    "description": "Optional project/classroom scope (e.g. classroom:<grant_id>).",
                },
                "top_k": {"type": "integer", "description": "Number of chunks to retrieve (1-10)."},
            },
            "required": ["query"],
        }

    async def execute(self, context: AgentContext, **kwargs: Any) -> ToolResult:
        if not settings.RAG_ENABLED:
            return ToolResult(content="rag_search: document RAG is disabled on this server.")

        query = str(kwargs.get("query") or "").strip()
        if not query:
            return ToolResult(content="rag_search: query is empty")
        if not context.user_id:
            return ToolResult(content="rag_search: authentication required")

        project_id = kwargs.get("project_id")
        top_k = int(kwargs.get("top_k") or settings.RAG_TOP_K)
        top_k = max(1, min(top_k, 10))

        async with resolve_agent_db(context) as db:
            service = RetrievalService()
            try:
                chunks = await service.retrieve(
                    db,
                    query,
                    access=AccessContext(
                        user_id=str(context.user_id),
                        project_id=str(project_id) if project_id else None,
                    ),
                    top_k=top_k,
                )
            except PermissionError:
                return ToolResult(content="rag_search: not authorized for this project scope.")
            if get_bound_db_session(context) is None:
                await db.commit()

        if not chunks:
            return ToolResult(content="No relevant document context was found in indexed documents.")

        builder = RagContextBuilder()
        content = builder.build_context_block(chunks, include_injection_guard=True)
        return ToolResult(
            content=content,
            metadata={
                "count": len(chunks),
                "chunk_ids": [c.chunk_id for c in chunks],
                "document_ids": list({c.document_id for c in chunks}),
            },
        )
