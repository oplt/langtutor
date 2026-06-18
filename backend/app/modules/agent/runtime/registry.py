from __future__ import annotations

import logging
from typing import Any

from backend.app.modules.agent.core.protocols import BaseCapability, BaseTool

logger = logging.getLogger(__name__)


class CapabilityRegistry:
    _ALIASES: dict[str, str] = {"tutor_chat": "chat"}

    def __init__(self) -> None:
        self._capabilities: dict[str, BaseCapability] = {}

    def register(self, capability: BaseCapability) -> None:
        self._capabilities[capability.name] = capability

    def get(self, name: str) -> BaseCapability | None:
        resolved = self._ALIASES.get(name, name)
        return self._capabilities.get(resolved)

    def list_capabilities(self) -> list[str]:
        names = list(self._capabilities.keys())
        for alias in self._ALIASES:
            if alias not in names:
                names.append(alias)
        return names

    def get_manifests(self) -> list[dict[str, Any]]:
        return [
            {"name": capability.name, "description": capability.description}
            for capability in self._capabilities.values()
        ]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())

    def get_enabled(self, names: list[str] | None) -> list[BaseTool]:
        if names is None:
            return list(self._tools.values())
        enabled: list[BaseTool] = []
        for name in names:
            tool = self._tools.get(name)
            if tool is not None:
                enabled.append(tool)
        return enabled

    def build_openai_schemas(self, names: list[str] | None = None) -> list[dict[str, Any]]:
        tools = self.get_enabled(names) if names is not None else list(self._tools.values())
        return [tool.get_definition().to_openai_schema() for tool in tools]

    async def execute(self, name: str, context, /, **kwargs: Any):
        tool = self._tools.get(name)
        if tool is None:
            raise KeyError(f"Unknown tool: {name}")
        return await tool.execute(context, **kwargs)


_capability_registry: CapabilityRegistry | None = None
_tool_registry: ToolRegistry | None = None


def get_capability_registry() -> CapabilityRegistry:
    global _capability_registry
    if _capability_registry is None:
        from backend.app.modules.agent.runtime.bootstrap import bootstrap_runtime

        _capability_registry = CapabilityRegistry()
        bootstrap_runtime(_capability_registry, get_tool_registry())
    return _capability_registry


def get_tool_registry() -> ToolRegistry:
    global _tool_registry
    if _tool_registry is None:
        from backend.app.modules.agent.runtime.bootstrap import bootstrap_tools

        _tool_registry = ToolRegistry()
        bootstrap_tools(_tool_registry)
    return _tool_registry
