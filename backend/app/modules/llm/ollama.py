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
from backend.app.modules.llm.errors import LLMConfigError, LLMNetworkError, LLMProviderUnavailableError
from backend.app.modules.llm.http import request_json, stream_post_lines


class OllamaClient(BaseLLMClient):
    async def health_check(self) -> LLMHealth:
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
            detail="Ollama reachable." if models else "Ollama reachable; no models found.",
            provider=self.config.provider,
            model_count=len(models),
        )

    async def list_models(self) -> list[LLMModel]:
        base = self.config.api_base.rstrip("/")
        url = f"{base}/api/tags"
        status, data = await request_json(
            "GET",
            url,
            timeout_seconds=self.config.timeout_seconds,
        )
        if status >= 400:
            raise LLMProviderUnavailableError(
                f"Ollama model discovery failed with HTTP {status}."
            )
        raw_models = data.get("models") if isinstance(data, dict) else []
        return [
            LLMModel(id=str(item.get("name")), name=str(item.get("name")), local=True)
            for item in raw_models
            if isinstance(item, dict) and item.get("name")
        ]

    async def chat(self, request: LLMChatRequest) -> LLMChatResponse:
        model = request.model or self.config.model
        if not model:
            raise LLMConfigError("Model is required.")
        messages = [
            {"role": message.role, "content": message.content}
            for message in request.messages
            if message.role in {"system", "user", "assistant"}
        ]
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": (
                    request.temperature
                    if request.temperature is not None
                    else self.config.temperature
                ),
                "num_predict": (
                    request.max_tokens
                    if request.max_tokens is not None
                    else self.config.max_tokens
                ),
            },
        }
        if request.tools:
            payload["tools"] = request.tools

        base = self.config.api_base.rstrip("/")
        status, data = await request_json(
            "POST",
            f"{base}/api/chat",
            body=payload,
            timeout_seconds=self.config.timeout_seconds,
        )
        if status >= 400:
            detail = data if isinstance(data, str) else json.dumps(data)
            raise LLMProviderUnavailableError(f"Ollama chat failed with HTTP {status}: {detail}")
        if not isinstance(data, dict):
            raise LLMNetworkError("Unexpected Ollama response shape.")

        message = data.get("message") or {}
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

        messages = [
            {"role": message.role, "content": message.content}
            for message in request.messages
            if message.role in {"system", "user", "assistant"}
        ]
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": (
                    request.temperature
                    if request.temperature is not None
                    else self.config.temperature
                ),
                "num_predict": (
                    request.max_tokens
                    if request.max_tokens is not None
                    else self.config.max_tokens
                ),
            },
        }
        base = self.config.api_base.rstrip("/")
        async for line in stream_post_lines(
            f"{base}/api/chat",
            body=payload,
            timeout_seconds=self.config.timeout_seconds,
        ):
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            message = event.get("message") or {}
            chunk = message.get("content")
            if chunk:
                yield str(chunk)

    @staticmethod
    def _parse_tool_calls(raw_calls: Any) -> list[LLMToolCall]:
        if not isinstance(raw_calls, list):
            return []
        parsed: list[LLMToolCall] = []
        for index, item in enumerate(raw_calls):
            if not isinstance(item, dict):
                continue
            fn = item.get("function") or item
            args_raw = fn.get("arguments") or "{}"
            try:
                args = json.loads(args_raw) if isinstance(args_raw, str) else dict(args_raw)
            except json.JSONDecodeError:
                args = {"raw": args_raw}
            parsed.append(
                LLMToolCall(
                    id=str(item.get("id") or f"call_{index}"),
                    name=str(fn.get("name") or item.get("name") or ""),
                    arguments=args if isinstance(args, dict) else {},
                )
            )
        return parsed
