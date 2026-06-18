from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from backend.app.modules.llm.base import (
    BaseLLMClient,
    LLMChatRequest,
    LLMChatResponse,
    LLMHealth,
    LLMModel,
    LLMToolCall,
)
from backend.app.modules.llm.errors import (
    LLMConfigError,
    LLMNetworkError,
    LLMProviderUnavailableError,
)
from backend.app.modules.llm.http import request_json, stream_post_lines


class OpenAICompatibleClient(BaseLLMClient):
    async def health_check(self) -> LLMHealth:
        if not self.config.api_base:
            return LLMHealth(
                ok=False,
                status="not_configured",
                detail="API base URL is required.",
                provider=self.config.provider,
            )
        try:
            models = await self.list_models()
        except Exception as exc:
            return LLMHealth(
                ok=False,
                status="unreachable",
                detail=str(exc),
                provider=self.config.provider,
            )
        return LLMHealth(
            ok=True,
            status="running",
            detail="Provider reachable.",
            provider=self.config.provider,
            model_count=len(models),
        )

    async def list_models(self) -> list[LLMModel]:
        url = f"{self.config.api_base.rstrip('/')}/models"
        status, data = await request_json(
            "GET",
            url,
            headers=self._headers(),
            timeout_seconds=self.config.timeout_seconds,
        )
        if status in {401, 403}:
            raise LLMProviderUnavailableError("Invalid API key or unauthorized.")
        if status >= 400:
            raise LLMProviderUnavailableError(f"Model discovery failed with HTTP {status}.")
        raw_models = data.get("data") if isinstance(data, dict) else None
        if not isinstance(raw_models, list):
            return []
        return [
            LLMModel(
                id=str(item.get("id")),
                name=str(item.get("id")),
                local=self.config.provider == "llama_cpp",
            )
            for item in raw_models
            if isinstance(item, dict) and item.get("id")
        ]

    async def chat(self, request: LLMChatRequest) -> LLMChatResponse:
        model = request.model or self.config.model
        if not model:
            raise LLMConfigError("Model is required.")
        payload: dict[str, Any] = {
            "model": model,
            "messages": [self._serialize_message(message) for message in request.messages],
            "temperature": (
                request.temperature
                if request.temperature is not None
                else self.config.temperature
            ),
            "max_tokens": (
                request.max_tokens
                if request.max_tokens is not None
                else self.config.max_tokens
            ),
            "stream": False,
        }
        if request.tools:
            payload["tools"] = request.tools
            payload["tool_choice"] = "auto"

        url = f"{self.config.api_base.rstrip('/')}/chat/completions"
        status, data = await request_json(
            "POST",
            url,
            headers=self._headers(),
            body=payload,
            timeout_seconds=self.config.timeout_seconds,
        )
        if status in {401, 403}:
            raise LLMProviderUnavailableError("Invalid API key or unauthorized.")
        if status == 404:
            raise LLMProviderUnavailableError("Chat endpoint or model not found.")
        if status >= 400:
            detail = data if isinstance(data, str) else json.dumps(data)
            raise LLMProviderUnavailableError(f"Chat failed with HTTP {status}: {detail}")

        if not isinstance(data, dict):
            raise LLMNetworkError("Unexpected chat response shape.")
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        tool_calls = self._parse_tool_calls(message.get("tool_calls"))
        return LLMChatResponse(
            provider=self.config.provider,
            model=model,
            content=str(message.get("content") or ""),
            tool_calls=tool_calls,
            raw=data,
        )

    async def stream_chat(self, request: LLMChatRequest) -> AsyncIterator[str]:
        model = request.model or self.config.model
        if not model:
            raise LLMConfigError("Model is required.")
        if request.tools:
            response = await self.chat(request)
            if response.content:
                yield response.content
            return

        payload: dict[str, Any] = {
            "model": model,
            "messages": [self._serialize_message(message) for message in request.messages],
            "temperature": (
                request.temperature
                if request.temperature is not None
                else self.config.temperature
            ),
            "max_tokens": (
                request.max_tokens
                if request.max_tokens is not None
                else self.config.max_tokens
            ),
            "stream": True,
        }
        url = f"{self.config.api_base.rstrip('/')}/chat/completions"
        async for line in stream_post_lines(
            url,
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
            choices = event.get("choices") or []
            if not choices:
                continue
            delta = (choices[0].get("delta") or {}).get("content")
            if delta:
                yield str(delta)

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        if self.config.organization:
            headers["OpenAI-Organization"] = self.config.organization
        if self.config.project:
            headers["OpenAI-Project"] = self.config.project
        return headers

    @staticmethod
    def _serialize_message(message) -> dict[str, Any]:
        payload: dict[str, Any] = {"role": message.role, "content": message.content}
        if message.tool_call_id:
            payload["tool_call_id"] = message.tool_call_id
        if message.name:
            payload["name"] = message.name
        if message.tool_calls:
            payload["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": json.dumps(call.arguments),
                    },
                }
                for call in message.tool_calls
            ]
        return payload

    @staticmethod
    def _parse_tool_calls(raw_calls: Any) -> list[LLMToolCall]:
        if not isinstance(raw_calls, list):
            return []
        parsed: list[LLMToolCall] = []
        for item in raw_calls:
            if not isinstance(item, dict):
                continue
            fn = item.get("function") or {}
            args_raw = fn.get("arguments") or "{}"
            try:
                args = json.loads(args_raw) if isinstance(args_raw, str) else dict(args_raw)
            except json.JSONDecodeError:
                args = {"raw": args_raw}
            parsed.append(
                LLMToolCall(
                    id=str(item.get("id") or ""),
                    name=str(fn.get("name") or ""),
                    arguments=args if isinstance(args, dict) else {},
                )
            )
        return parsed
