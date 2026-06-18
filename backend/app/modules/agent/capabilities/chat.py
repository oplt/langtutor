from __future__ import annotations

from backend.app.modules.agent.chat.pipeline import ChatPipeline
from backend.app.modules.agent.core.context import AgentContext
from backend.app.modules.agent.core.protocols import BaseCapability
from backend.app.modules.agent.core.stream_bus import StreamBus


class ChatCapability(BaseCapability):
    name = "chat"
    description = (
        "Agentic Dutch tutor chat: explanations, corrections, and interactive drills."
    )

    async def run(self, context: AgentContext, bus: StreamBus) -> None:
        pipeline = ChatPipeline(llm_task="tutor_chat", source="chat")
        await pipeline.run(context, bus)
