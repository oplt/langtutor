from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, AsyncIterator

from backend.app.modules.agent.core.context import AgentContext
from backend.app.modules.agent.core.stream import StreamEvent, StreamEventType
from backend.app.modules.agent.core.stream_bus import StreamBus
from backend.app.modules.agent.runtime.registry import get_capability_registry, get_tool_registry

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Routes AgentContext to capabilities and streams turn events."""

    def __init__(self) -> None:
        self._capabilities = get_capability_registry()
        self._tools = get_tool_registry()

    async def handle(self, context: AgentContext) -> AsyncIterator[StreamEvent]:
        if not context.session_id:
            context.session_id = str(uuid.uuid4())

        cap_name = context.active_capability or "chat"
        capability = self._capabilities.get(cap_name)
        if capability is None:
            bus = StreamBus()
            await bus.error(
                f"Unknown capability: {cap_name}. "
                f"Available: {self._capabilities.list_capabilities()}",
                source="orchestrator",
            )
            await bus.close()
            async for event in bus.subscribe():
                yield event
            return

        yield StreamEvent(
            type=StreamEventType.SESSION,
            source="orchestrator",
            metadata={
                "session_id": context.session_id,
                "capability": cap_name,
                "turn_id": str(context.metadata.get("turn_id", "")),
            },
        )

        bus = StreamBus()

        async def _run() -> None:
            try:
                await capability.run(context, bus)
            except Exception as exc:
                logger.error("Capability %s failed: %s", cap_name, exc, exc_info=True)
                await bus.error(str(exc), source=cap_name)
            finally:
                await bus.emit(StreamEvent(type=StreamEventType.DONE, source=cap_name))
                await bus.close()

        stream = bus.subscribe()
        task = asyncio.create_task(_run())
        async for event in stream:
            yield event
        await task

    def list_tools(self) -> list[str]:
        return self._tools.list_tools()

    def list_capabilities(self) -> list[str]:
        return self._capabilities.list_capabilities()

    def get_capability_manifests(self) -> list[dict[str, Any]]:
        return self._capabilities.get_manifests()

    def get_tool_schemas(self, names: list[str] | None = None) -> list[dict[str, Any]]:
        return self._tools.build_openai_schemas(names)
