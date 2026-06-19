from __future__ import annotations

from backend.app.modules.agent.capabilities.chat import ChatCapability
from backend.app.modules.agent.capabilities.deep_research import (
    DeepResearchCapability,
)
from backend.app.modules.agent.capabilities.mastery_path import MasteryPathCapability
from backend.app.modules.agent.capabilities.deep_solve import DeepSolveCapability
from backend.app.modules.agent.capabilities.visualize import VisualizeCapability
from backend.app.modules.agent.runtime.registry import CapabilityRegistry, ToolRegistry
from backend.app.modules.agent.tools.ask_user import AskUserTool
from backend.app.modules.agent.tools.knowledge import SearchKnowledgeTool
from backend.app.modules.agent.tools.rag_search import RagSearchTool
from backend.app.modules.agent.tools.sandbox_eval import SandboxEvalTool
from backend.app.modules.agent.tools.mastery import MasteryGradeTool, MasteryStatusTool
from backend.app.modules.agent.tools.memory import ReadMemoryTool, WriteMemoryTool
from backend.app.modules.agent.tools.notebook import SaveToNotebookTool
from backend.app.modules.agent.tools.vision_ocr import VisionOcrTool
from backend.app.modules.extensions.plugins.tools import LookupDictionaryTool


def bootstrap_tools(tool_registry: ToolRegistry) -> None:
    tool_registry.register(AskUserTool())
    tool_registry.register(SearchKnowledgeTool())
    tool_registry.register(MasteryStatusTool())
    tool_registry.register(MasteryGradeTool())
    tool_registry.register(ReadMemoryTool())
    tool_registry.register(WriteMemoryTool())
    tool_registry.register(SaveToNotebookTool())
    tool_registry.register(VisionOcrTool())
    tool_registry.register(SandboxEvalTool())
    tool_registry.register(LookupDictionaryTool())
    tool_registry.register(RagSearchTool())


def bootstrap_runtime(capability_registry: CapabilityRegistry, tool_registry: ToolRegistry) -> None:
    _ = tool_registry
    capability_registry.register(ChatCapability())
    capability_registry.register(MasteryPathCapability())
    capability_registry.register(DeepResearchCapability())
    capability_registry.register(DeepSolveCapability())
    capability_registry.register(VisualizeCapability())
