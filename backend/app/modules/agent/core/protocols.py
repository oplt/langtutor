from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from backend.app.modules.agent.core.context import AgentContext
from backend.app.modules.agent.core.stream_bus import StreamBus


@dataclass
class ToolResult:
    content: str
    pause_for_user: bool = False
    pause_question: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
                or {"type": "object", "properties": {}, "required": []},
            },
        }


class BaseTool(ABC):
    name: str = ""
    description: str = ""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=self.parameters(),
        )

    def parameters(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}, "required": []}

    @abstractmethod
    async def execute(self, context: AgentContext, **kwargs: Any) -> ToolResult:
        raise NotImplementedError


class BaseCapability(ABC):
    name: str = ""
    description: str = ""

    @abstractmethod
    async def run(self, context: AgentContext, bus: StreamBus) -> None:
        raise NotImplementedError
