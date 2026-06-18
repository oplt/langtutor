from __future__ import annotations

from backend.app.modules.agent.chat.pipeline import ChatPipeline
from backend.app.modules.agent.capabilities.chat import ChatCapability
from backend.app.modules.agent.core.context import AgentContext
from backend.app.modules.agent.core.stream_bus import StreamBus

RESEARCH_TOOLS = ["ask_user", "rag", "read_memory", "write_memory"]

RESEARCH_PROMPT = """
## Deep research mode
You are writing a short, well-structured cultural or historical essay for an advanced Dutch learner.
- Call `rag` first to ground facts in the knowledge base when relevant.
- Organize with headings: Context, Key points, Dutch vocabulary highlights, Discussion questions.
- Cite uncertainty when sources are thin; do not invent historical facts.
- Keep essays focused (400–700 words unless the learner asks for more).
- Include 5–8 useful Dutch phrases or terms with brief English glosses.
""".strip()


class DeepResearchCapability(ChatCapability):
    name = "deep_research"
    description = (
        "Cultural context essays and Netherlands history for advanced learners."
    )

    async def run(self, context: AgentContext, bus: StreamBus) -> None:
        context.metadata["research_mode"] = True
        if context.enabled_tools is None:
            context.enabled_tools = list(RESEARCH_TOOLS)
        extra = str(context.metadata.get("extra_system_prompt") or "")
        context.metadata["extra_system_prompt"] = f"{extra}\n\n{RESEARCH_PROMPT}".strip()
        pipeline = ChatPipeline(llm_task="tutor_chat", source="deep_research")
        await pipeline.run(context, bus)
