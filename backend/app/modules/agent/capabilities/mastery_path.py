from __future__ import annotations

from backend.app.modules.agent.chat.pipeline import ChatPipeline
from backend.app.modules.agent.capabilities.chat import ChatCapability
from backend.app.modules.agent.core.context import AgentContext
from backend.app.modules.agent.core.stream_bus import StreamBus

MASTERY_TOOLS = ["ask_user", "mastery_status", "mastery_grade"]


class MasteryPathCapability(ChatCapability):
    name = "mastery_path"
    description = (
        "Dutch tutor with deterministic mastery path: vocab, grammar, dialogue, gate."
    )

    async def run(self, context: AgentContext, bus: StreamBus) -> None:
        context.metadata["mastery_mode"] = True
        if context.enabled_tools is None:
            context.enabled_tools = list(MASTERY_TOOLS)
        pipeline = ChatPipeline(llm_task="tutor_chat", source="mastery_path")
        await pipeline.run(context, bus)
