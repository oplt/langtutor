from __future__ import annotations

import logging

from backend.app.modules.llm.base import LLMMessage

logger = logging.getLogger(__name__)

_CHARS_PER_TOKEN = 4
_MIN_RESERVED_TOKENS = 512
_SUMMARY_PREFIX = "[Earlier conversation summarized]"


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return max(1, len(text) // _CHARS_PER_TOKEN)


def estimate_messages_tokens(messages: list[LLMMessage]) -> int:
    total = 0
    for message in messages:
        total += 4
        total += estimate_tokens(message.content)
    return total


def _summarize_dropped_messages(messages: list[LLMMessage]) -> str:
    lines: list[str] = []
    for message in messages:
        role = message.role
        content = " ".join(message.content.split())
        if not content:
            continue
        if len(content) > 120:
            content = content[:117] + "..."
        lines.append(f"- {role}: {content}")
        if len(lines) >= 6:
            break
    if not lines:
        return f"{_SUMMARY_PREFIX} prior turns omitted to fit the context window."
    return f"{_SUMMARY_PREFIX}\n" + "\n".join(lines)


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
    dropped_other: list[LLMMessage] = []
    for message in reversed(other_messages):
        cost = estimate_tokens(message.content) + 4
        if used + cost > budget:
            dropped_other.insert(0, message)
            continue
        kept_other.insert(0, message)
        used += cost

    if dropped_other:
        summary = LLMMessage(role="system", content=_summarize_dropped_messages(dropped_other))
        summary_cost = estimate_tokens(summary.content) + 4
        while kept_other and used + summary_cost > budget:
            dropped_other.insert(0, kept_other.pop(0))
            summary = LLMMessage(role="system", content=_summarize_dropped_messages(dropped_other))
            summary_cost = estimate_tokens(summary.content) + 4
        if used + summary_cost <= budget:
            kept_system.append(summary)
            used += summary_cost

    result = [*kept_system, *kept_other]
    after_tokens = estimate_messages_tokens(result)
    if after_tokens < before_tokens:
        logger.info(
            "llm_context_truncated task=%s before_tokens=%s after_tokens=%s budget=%s dropped=%s",
            task or "unknown",
            before_tokens,
            after_tokens,
            budget,
            len(dropped_other),
        )
    return result
