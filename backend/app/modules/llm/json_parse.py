from __future__ import annotations

import json
import re
from typing import Any


class LLMJsonParseError(ValueError):
    """Raised when an LLM response cannot be parsed as a JSON object."""


def _strip_markdown_fence(text: str) -> str:
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
    if fence:
        return fence.group(1).strip()
    return text.strip()


def _iter_object_candidates(text: str) -> list[str]:
    cleaned = _strip_markdown_fence(text)
    candidates: list[str] = []
    if cleaned:
        candidates.append(cleaned)
    for match in re.finditer(r"\{", text):
        start = match.start()
        fragment = text[start:]
        if fragment not in candidates:
            candidates.append(fragment)
    return candidates


def _decode_first_object(candidate: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    index = 0
    length = len(candidate)
    while index < length:
        next_brace = candidate.find("{", index)
        if next_brace < 0:
            break
        try:
            payload, _end = decoder.raw_decode(candidate, next_brace)
        except json.JSONDecodeError:
            index = next_brace + 1
            continue
        if isinstance(payload, dict):
            return payload
        index = next_brace + 1
    raise LLMJsonParseError("No JSON object found in LLM response.")


def extract_json_object(raw: str) -> dict[str, Any]:
    """Extract the first valid JSON object from LLM output with surrounding text."""
    text = (raw or "").strip()
    if not text:
        raise LLMJsonParseError("Empty LLM response.")

    errors: list[str] = []
    for candidate in _iter_object_candidates(text):
        try:
            return _decode_first_object(candidate)
        except LLMJsonParseError as exc:
            errors.append(str(exc))
        except json.JSONDecodeError as exc:
            errors.append(str(exc))

    raise LLMJsonParseError(errors[-1] if errors else "No JSON object found in LLM response.")


def repair_json_prompt(invalid_response: str) -> str:
    return (
        "The previous response was invalid JSON. Return ONLY a valid JSON object. "
        "Do not include markdown fences, commentary, or extra text.\n"
        f"Invalid response:\n{invalid_response[:4000]}"
    )
