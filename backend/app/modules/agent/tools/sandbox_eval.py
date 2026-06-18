from __future__ import annotations

import json
from typing import Any

from backend.app.modules.agent.core.context import AgentContext
from backend.app.modules.agent.core.protocols import BaseTool, ToolResult
from backend.app.modules.extensions.sandbox.service import run_sandbox_expression


class SandboxEvalTool(BaseTool):
    name = "sandbox_eval"
    description = (
        "Safely evaluate a small arithmetic expression using a restricted sandbox. "
        "Use to check math steps without allowing arbitrary code execution."
    )

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Arithmetic expression to evaluate (e.g. (3+4)*2).",
                }
            },
            "required": ["expression"],
        }

    async def execute(self, context: AgentContext, **kwargs: Any) -> ToolResult:
        _ = context
        expression = str(kwargs.get("expression") or "").strip()
        result = run_sandbox_expression(expression)
        return ToolResult(
            content=json.dumps(result, ensure_ascii=False),
            metadata={"tool": self.name, "ok": bool(result.get("ok"))},
        )

