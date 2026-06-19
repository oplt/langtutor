from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass

from backend.app.core.config import settings
from backend.app.core.metrics import metrics_registry
from backend.app.modules.llm.base import (
    BaseLLMClient,
    LLMChatRequest,
    LLMChatResponse,
    LLMProviderConfig,
)
from backend.app.modules.llm.context_guard import estimate_messages_tokens, estimate_tokens, fit_messages

logger = logging.getLogger(__name__)


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
        model = prepared.model or self.config.model
        logger.info(
            "llm_request_started",
            extra={
                "task": self.task,
                "provider": self.config.provider,
                "model": model,
                "message_count": len(prepared.messages),
            },
        )
        try:
            response = await self.client.chat(prepared)
            output_tokens = estimate_tokens(response.content)
            success = True
            return response
        except Exception:
            logger.exception(
                "llm_request_failed",
                extra={
                    "task": self.task,
                    "provider": self.config.provider,
                    "model": model,
                },
            )
            raise
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            metrics_registry.observe_llm_call(
                task=self.task,
                provider=self.config.provider,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                duration_ms=duration_ms,
                success=success,
            )
            extra = {
                "task": self.task,
                "provider": self.config.provider,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "duration_ms": duration_ms,
                "success": success,
            }
            if success:
                if duration_ms >= settings.SLOW_EXTERNAL_CALL_MS:
                    logger.warning("llm_request_slow", extra=extra)
                else:
                    logger.info("llm_request_complete", extra=extra)

    async def stream_chat(self, request: LLMChatRequest) -> AsyncIterator[str]:
        prepared = self._prepare_request(request, stream=True)
        start = time.perf_counter()
        input_tokens = estimate_messages_tokens(prepared.messages)
        output_tokens = 0
        success = False
        model = prepared.model or self.config.model
        logger.info(
            "llm_stream_started",
            extra={
                "task": self.task,
                "provider": self.config.provider,
                "model": model,
                "message_count": len(prepared.messages),
            },
        )
        try:
            async for chunk in self.client.stream_chat(prepared):
                output_tokens += estimate_tokens(chunk)
                yield chunk
            success = True
        except Exception:
            logger.exception(
                "llm_stream_failed",
                extra={
                    "task": self.task,
                    "provider": self.config.provider,
                    "model": model,
                },
            )
            raise
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            metrics_registry.observe_llm_call(
                task=self.task,
                provider=self.config.provider,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                duration_ms=duration_ms,
                success=success,
            )
            extra = {
                "task": self.task,
                "provider": self.config.provider,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "duration_ms": duration_ms,
                "success": success,
            }
            if success:
                if duration_ms >= settings.SLOW_EXTERNAL_CALL_MS:
                    logger.warning("llm_stream_slow", extra=extra)
                else:
                    logger.info("llm_stream_complete", extra=extra)

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
