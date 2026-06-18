from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
import time

from backend.app.core.metrics import metrics_registry
from backend.app.modules.llm.base import (
    BaseLLMClient,
    LLMChatRequest,
    LLMChatResponse,
    LLMProviderConfig,
)
from backend.app.modules.llm.context_guard import estimate_messages_tokens, estimate_tokens, fit_messages


@dataclass
class LLMTaskClient:
    task: str
    client: BaseLLMClient
    config: LLMProviderConfig

    async def chat(self, request: LLMChatRequest) -> LLMChatResponse:
        prepared = self._prepare_request(request, stream=False)
        start = time.perf_counter()
        input_tokens = estimate_messages_tokens(prepared.messages)
        output_tokens = 0
        success = False
        try:
            response = await self.client.chat(prepared)
            output_tokens = estimate_tokens(response.content)
            success = True
            return response
        finally:
            metrics_registry.observe_llm_call(
                task=self.task,
                provider=self.config.provider,
                model=prepared.model or self.config.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                duration_ms=(time.perf_counter() - start) * 1000,
                success=success,
            )

    async def stream_chat(self, request: LLMChatRequest) -> AsyncIterator[str]:
        prepared = self._prepare_request(request, stream=True)
        start = time.perf_counter()
        input_tokens = estimate_messages_tokens(prepared.messages)
        output_tokens = 0
        success = False
        try:
            async for chunk in self.client.stream_chat(prepared):
                output_tokens += estimate_tokens(chunk)
                yield chunk
            success = True
        finally:
            metrics_registry.observe_llm_call(
                task=self.task,
                provider=self.config.provider,
                model=prepared.model or self.config.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                duration_ms=(time.perf_counter() - start) * 1000,
                success=success,
            )

    def _prepare_request(self, request: LLMChatRequest, *, stream: bool) -> LLMChatRequest:
        messages = fit_messages(
            request.messages,
            self.config.context_window,
            task=self.task,
        )
        return request.model_copy(
            update={
                "messages": messages,
                "model": request.model or self.config.model,
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
                "stream": stream,
            }
        )
