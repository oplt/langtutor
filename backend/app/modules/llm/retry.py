from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import AsyncIterator

from backend.app.modules.llm.base import (
    BaseLLMClient,
    LLMChatRequest,
    LLMChatResponse,
    LLMHealth,
    LLMModel,
)
from backend.app.modules.llm.errors import LLMNetworkError, LLMProviderUnavailableError
from backend.app.modules.llm.circuit_breaker import get_llm_circuit_breaker

logger = logging.getLogger(__name__)

_RETRYABLE_STATUS_HINTS = {"timeout", "unreachable", "503", "502", "429"}


class RetryLLMClient(BaseLLMClient):
    def __init__(
        self,
        inner: BaseLLMClient,
        *,
        max_attempts: int = 3,
        base_delay_seconds: float = 0.5,
    ) -> None:
        super().__init__(inner.config)
        self._inner = inner
        self._max_attempts = max(1, max_attempts)
        self._base_delay_seconds = base_delay_seconds

    @property
    def _breaker(self):
        return get_llm_circuit_breaker(self.config.provider)

    async def health_check(self) -> LLMHealth:
        return await self._inner.health_check()

    async def list_models(self) -> list[LLMModel]:
        return await self._with_retry(self._inner.list_models)

    async def chat(self, request: LLMChatRequest) -> LLMChatResponse:
        if not self._breaker.allow():
            raise LLMProviderUnavailableError("LLM circuit open — provider temporarily unavailable.")
        try:
            response = await self._with_retry(self._inner.chat, request)
        except Exception:
            self._breaker.record_failure()
            raise
        self._breaker.record_success()
        return response

    async def stream_chat(self, request: LLMChatRequest) -> AsyncIterator[str]:
        if not self._breaker.allow():
            raise LLMProviderUnavailableError("LLM circuit open — provider temporarily unavailable.")
        attempt = 0
        while True:
            attempt += 1
            saw_output = False
            try:
                async for chunk in self._inner.stream_chat(request):
                    saw_output = True
                    yield chunk
                self._breaker.record_success()
                return
            except Exception as exc:
                if saw_output or attempt >= self._max_attempts or not self._is_retryable(exc):
                    self._breaker.record_failure()
                    raise
                delay = self._backoff_delay(attempt)
                logger.warning(
                    "LLM stream retry %s/%s after %ss: %s",
                    attempt,
                    self._max_attempts,
                    delay,
                    exc,
                )
                await asyncio.sleep(delay)

    async def _with_retry(self, fn, *args, **kwargs):
        attempt = 0
        while True:
            attempt += 1
            try:
                return await fn(*args, **kwargs)
            except Exception as exc:
                if attempt >= self._max_attempts or not self._is_retryable(exc):
                    raise
                delay = self._backoff_delay(attempt)
                logger.warning(
                    "LLM request retry %s/%s after %ss: %s",
                    attempt,
                    self._max_attempts,
                    delay,
                    exc,
                )
                await asyncio.sleep(delay)

    def _backoff_delay(self, attempt: int) -> float:
        jitter = random.uniform(0.0, 0.25)
        return self._base_delay_seconds * (2 ** (attempt - 1)) + jitter

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        if isinstance(exc, LLMNetworkError):
            return True
        if isinstance(exc, LLMProviderUnavailableError):
            text = f"{exc} {getattr(exc, 'detail', '')}".lower()
            return any(hint in text for hint in _RETRYABLE_STATUS_HINTS)
        return False
