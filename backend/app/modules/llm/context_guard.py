from __future__ import annotations

import logging

from backend.app.modules.llm.base import LLMMessage

logger = logging.getLogger(__name__)

_CHARS_PER_TOKEN = 4
_MIN_RESERVED_TOKENS = 512


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // _CHARS_PER_TOKEN)


def estimate_messages_tokens(messages: list[LLMMessage]) -> int:
    total = 0
    for message in messages:
        total += 4  # role/overhead
        total += estimate_tokens(message.content)
    return total


def fit_messages(
    messages: list[LLMMessage],
    context_window: int,
    *,
    reserve_tokens: int = _MIN_RESERVED_TOKENS,
    task: str = "",
) -> list[LLMMessage]:
    if context_window <= 0:
        return messages

    before_tokens = estimate_messages_tokens(messages)
    budget = max(context_window - reserve_tokens, 256)
    if before_tokens <= budget:
        return messages

    system_messages = [message for message in messages if message.role == "system"]
    other_messages = [message for message in messages if message.role != "system"]

    kept_system: list[LLMMessage] = []
    used = 0
    for message in system_messages:
        cost = estimate_tokens(message.content) + 4
        if used + cost > budget:
            break
        kept_system.append(message)
        used += cost

    kept_other: list[LLMMessage] = []
    for message in reversed(other_messages):
        cost = estimate_tokens(message.content) + 4
        if used + cost > budget:
            break
        kept_other.insert(0, message)
        used += cost

    result = [*kept_system, *kept_other]
    after_tokens = estimate_messages_tokens(result)
    if after_tokens < before_tokens:
        logger.info(
            "llm_context_truncated task=%s before_tokens=%s after_tokens=%s budget=%s",
            task or "unknown",
            before_tokens,
            after_tokens,
            budget,
        )
    return result
