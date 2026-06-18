from backend.app.modules.agent.runtime.registry import CapabilityRegistry
from backend.app.modules.agent.core.protocols import BaseCapability
from backend.app.modules.agent.core.context import AgentContext
from backend.app.modules.agent.core.stream_bus import StreamBus


class _StubCapability(BaseCapability):
    name = "chat"
    description = "stub"

    async def run(self, context: AgentContext, bus: StreamBus) -> None:
        return None


def test_capability_registry_resolves_tutor_chat_alias() -> None:
    registry = CapabilityRegistry()
    registry.register(_StubCapability())
    assert registry.get("tutor_chat") is not None
    assert "tutor_chat" in registry.list_capabilities()
