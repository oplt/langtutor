"""Simple circuit breaker for LLM provider calls (Ollama / remote outages)."""

from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)

_FAILURE_THRESHOLD = 3
_COOLDOWN_SECONDS = 30.0


class LLMCircuitBreaker:
    def __init__(self) -> None:
        self._failures = 0
        self._opened_at: float | None = None

    def allow(self) -> bool:
        if self._opened_at is None:
            return True
        if time.monotonic() - self._opened_at >= _COOLDOWN_SECONDS:
            self._opened_at = None
            self._failures = 0
            logger.info("llm_circuit_half_open")
            return True
        return False

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= _FAILURE_THRESHOLD and self._opened_at is None:
            self._opened_at = time.monotonic()
            logger.warning("llm_circuit_open failures=%s", self._failures)


_breaker = LLMCircuitBreaker()


def get_llm_circuit_breaker() -> LLMCircuitBreaker:
    return _breaker
