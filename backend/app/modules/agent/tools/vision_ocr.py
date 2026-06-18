from __future__ import annotations

from typing import Any

from backend.app.modules.agent.core.context import AgentContext
from backend.app.modules.agent.core.protocols import BaseTool, ToolResult
from backend.app.modules.extensions.vision.service import extract_text_from_image


class VisionOcrTool(BaseTool):
    name = "vision_ocr"
    description = (
        "Extract Dutch text from a learner-provided image (base64) for immersion practice. "
        "Returns the extracted text plus a short tutoring prompt. "
        "Use when the learner asks to read/understand text from a photo."
    )

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "image_base64": {
                    "type": "string",
                    "description": "Base64 encoded image. May be a raw base64 string or data URL.",
                },
                "text": {
                    "type": "string",
                    "description": "Optional: provide text directly when OCR is unnecessary.",
                },
            },
            "required": [],
        }

    async def execute(self, context: AgentContext, **kwargs: Any) -> ToolResult:
        _ = context
        text = str(kwargs.get("text") or "").strip()
        meta: dict[str, Any] = {}

        if not text:
            image_base64 = str(kwargs.get("image_base64") or "").strip()
            if not image_base64:
                return ToolResult(content="vision_ocr: provide `image_base64` or `text`.")

            text, meta = extract_text_from_image(image_base64)

        if not text:
            meta.setdefault("hint", "OCR returned no extractable text.")

        return ToolResult(
            content=text or "",
            metadata={"tool": self.name, "meta": meta},
        )

