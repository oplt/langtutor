from __future__ import annotations

from typing import Any

from backend.app.modules.agent.core.context import AgentContext
from backend.app.modules.agent.core.protocols import BaseTool, ToolResult
from backend.app.modules.agent.tools.ask_user_payload import build_ask_user_payload


class AskUserTool(BaseTool):
    name = "ask_user"
    description = (
        "Pause the turn to ask the learner 1-4 questions in one card. Use for "
        "comprehension checks, drills, or when you genuinely need their answer "
        "before continuing. The loop resumes when they reply."
    )

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "intro": {
                    "type": "string",
                    "description": "Optional short intro shown above the questions.",
                },
                "questions": {
                    "type": "array",
                    "description": "1-4 questions. Bundle all clarifications in one call.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "prompt": {
                                "type": "string",
                                "description": "The question text.",
                            },
                            "header": {
                                "type": "string",
                                "description": "Short tab label (max 12 chars).",
                            },
                            "options": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "label": {"type": "string"},
                                        "description": {"type": "string"},
                                    },
                                    "required": ["label"],
                                },
                            },
                            "multi_select": {"type": "boolean"},
                            "allow_free_text": {"type": "boolean"},
                            "placeholder": {"type": "string"},
                        },
                        "required": ["prompt"],
                    },
                },
                "question": {
                    "type": "string",
                    "description": "Legacy single-question field (use questions instead).",
                },
            },
            "required": ["questions"],
        }

    async def execute(self, context: AgentContext, **kwargs: Any) -> ToolResult:
        payload, error = build_ask_user_payload(
            questions=kwargs.get("questions"),
            intro=kwargs.get("intro"),
            question=kwargs.get("question"),
            options=kwargs.get("options"),
        )
        if error or payload is None:
            return ToolResult(content=f"ask_user failed: {error or 'invalid payload'}")

        question_text = payload.primary_prompt
        return ToolResult(
            content=question_text,
            pause_for_user=True,
            pause_question=question_text,
            metadata={"tool": self.name, "ask_user": payload.to_dict()},
        )
