from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from backend.app.modules.llm.base import (
    BaseLLMClient,
    LLMChatRequest,
    LLMChatResponse,
    LLMHealth,
    LLMMessage,
    LLMModel,
)
from backend.app.modules.llm.errors import LLMConfigError, LLMNetworkError, LLMProviderUnavailableError
from backend.app.modules.llm.http import request_json, stream_post_lines


class AnthropicClient(BaseLLMClient):
    async def health_check(self) -> LLMHealth:
        if not self.config.api_key:
            return LLMHealth(
                ok=False,
                status="not_configured",
                detail="Anthropic API key is required.",
                provider=self.config.provider,
            )
        return LLMHealth(
            ok=True,
            status="configured",
            detail="Anthropic credentials configured.",
            provider=self.config.provider,
        )

    async def list_models(self) -> list[LLMModel]:
        model = self.config.model
        if not model:
            return []
        return [LLMModel(id=model, name=model)]

    async def chat(self, request: LLMChatRequest) -> LLMChatResponse:
        model = request.model or self.config.model
        if not model:
            raise LLMConfigError("Model is required.")
        system_text, messages = self._to_anthropic_messages(request.messages)
        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": request.max_tokens or self.config.max_tokens,
            "temperature": request.temperature if request.temperature is not None else self.config.temperature,
            "messages": messages,
        }
        if system_text:
            payload["system"] = system_text

        status, data = await request_json(
            "POST",
            f"{self.config.api_base.rstrip('/')}/v1/messages",
            headers=self._headers(),
            body=payload,
            timeout_seconds=self.config.timeout_seconds,
        )
        if status >= 400:
            detail = data if isinstance(data, str) else json.dumps(data)
            raise LLMProviderUnavailableError(f"Anthropic chat failed with HTTP {status}: {detail}")
        if not isinstance(data, dict):
            raise LLMNetworkError("Unexpected Anthropic response shape.")

        content_blocks = data.get("content") or []
        text = "".join(
            str(block.get("text") or "")
            for block in content_blocks
            if isinstance(block, dict) and block.get("type") == "text"
        )
        return LLMChatResponse(
            provider=self.config.provider,
            model=model,
            content=text,
            raw=data,
        )

    async def stream_chat(self, request: LLMChatRequest) -> AsyncIterator[str]:
        model = request.model or self.config.model
        if not model:
            raise LLMConfigError("Model is required.")
        system_text, messages = self._to_anthropic_messages(request.messages)
        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": request.max_tokens or self.config.max_tokens,
            "temperature": request.temperature if request.temperature is not None else self.config.temperature,
            "messages": messages,
            "stream": True,
        }
        if system_text:
            payload["system"] = system_text

        async for line in stream_post_lines(
            f"{self.config.api_base.rstrip('/')}/v1/messages",
            headers=self._headers(),
            body=payload,
            timeout_seconds=self.config.timeout_seconds,
        ):
            if not line.startswith("data:"):
                continue
            raw = line[5:].strip()
            if not raw or raw == "[DONE]":
                continue
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "content_block_delta":
                delta = event.get("delta") or {}
                text = delta.get("text")
                if text:
                    yield str(text)

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
        }

    @staticmethod
    def _to_anthropic_messages(messages: list[LLMMessage]) -> tuple[str, list[dict[str, str]]]:
        system_parts: list[str] = []
        converted: list[dict[str, str]] = []
        for message in messages:
            if message.role == "system":
                system_parts.append(message.content)
                continue
            if message.role in {"user", "assistant"}:
                converted.append({"role": message.role, "content": message.content})
        return "\n\n".join(system_parts), converted
