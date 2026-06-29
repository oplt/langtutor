from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from backend.app.modules.reading.schemas import Strictness
from backend.app.modules.reading.text_analyzer import analyze_coverage, classify_token, tokenize
from backend.app.modules.reading.vocabulary_normalizer import find_allowed_form, normalize_token_for_lookup, normalize_word

logger = logging.getLogger(__name__)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_WORD_RE = re.compile(r"['‘’]?[A-Za-zÀ-ÖØ-öø-ÿ]+(?:['‘’][A-Za-zÀ-ÖØ-öø-ÿ]+)?")


@dataclass(frozen=True)
class RuleAdaptationResult:
    adapted_text: str
    summary: str
    replacements: list[dict[str, str]]
    glossary: list[dict[str, str]]


def _try_lookup_form(token: str, allowed: set[str]) -> tuple[str | None, str]:
    """Best-effort lookup for inflected forms.

    This is used for recognition/glossary only. It avoids aggressive text
    replacement because crude stemming can produce ungrammatical Dutch.
    """
    normalized = normalize_token_for_lookup(token)
    recognized = find_allowed_form(normalized, allowed)
    if not recognized:
        return None, ""
    if recognized == normalized:
        return recognized, "already allowed"
    return recognized, f"recognized as a form related to '{recognized}'"


def _sentence_coverage(sentence: str, allowed: set[str]) -> float:
    result = analyze_coverage(sentence, allowed)
    if result.total_words == 0:
        return 1.0
    recognized_extra = 0
    for token in tokenize(sentence):
        category = classify_token(token, allowed)
        if category != "unknown":
            continue
        replacement, _ = _try_lookup_form(token, allowed)
        if replacement:
            recognized_extra += 1
    return min(1.0, (result.allowed_words + recognized_extra) / result.total_words)


def _max_sentence_words(level: int, strictness: Strictness) -> int | None:
    if strictness == "natural" and level >= 4:
        return None
    if level <= 1:
        return 10 if strictness == "strict" else 14
    if level <= 2:
        return 14 if strictness == "strict" else 18
    if level <= 3:
        return 18 if strictness == "strict" else 22
    return 26 if strictness == "strict" else None


def _min_sentence_coverage(level: int, strictness: Strictness) -> float:
    if strictness == "strict":
        return 0.92 if level <= 2 else 0.85
    if strictness == "balanced":
        return 0.82 if level <= 2 else 0.74
    return 0.68 if level <= 2 else 0.58


def _clip_to_word_count_at_sentence_boundary(sentences: list[str], word_count: int) -> str:
    selected: list[str] = []
    total = 0
    for sentence in sentences:
        sentence_words = sentence.split()
        if selected and total + len(sentence_words) > word_count:
            break
        selected.append(sentence)
        total += len(sentence_words)
    if not selected and sentences:
        words = sentences[0].split()[:word_count]
        text = " ".join(words).strip()
        return text if text.endswith((".", "!", "?")) else f"{text}."
    return " ".join(selected).strip()


def _build_glossary(
    text: str,
    allowed: set[str],
    word_metadata: dict[str, dict[str, str]],
    *,
    limit: int = 40,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    glossary: list[dict[str, str]] = []
    replacements: list[dict[str, str]] = []
    seen: set[str] = set()

    for match in _WORD_RE.finditer(text):
        token = match.group(0)
        category = classify_token(token, allowed)
        if category in {"allowed", "stopword", "number", "punctuation", "proper_noun"}:
            continue

        normalized = normalize_word(token)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)

        recognized, reason = _try_lookup_form(token, allowed)
        if recognized:
            replacements.append(
                {
                    "original": token,
                    "replacement": recognized,
                    "reason": reason or "recognized as an allowed word form",
                }
            )
            continue

        meta = word_metadata.get(normalized, {})
        translation = str(meta.get("translation", "")).strip(" ,")
        glossary.append(
            {
                "word": token,
                "definition": translation or "Important topic word outside the selected level.",
                "exampleSentence": "",
                "reasonKept": "outside selected level; kept for meaning",
            }
        )
        if len(glossary) >= limit:
            break

    return replacements, glossary


def adapt_text_with_rules(
    *,
    source_text: str,
    allowed_words: set[str],
    word_metadata: dict[str, dict[str, str]],
    level: int,
    word_count: int,
    strictness: Strictness,
    title: str = "",
) -> RuleAdaptationResult:
    """Fallback when no LLM is available.

    This function does not pretend to be a synonym-based simplifier. It keeps
    the clearest sentences, avoids crude stem replacement, clips on sentence
    boundaries, and explains unknown words in a glossary.
    """
    source_text = (source_text or "").strip()
    sentences = [part.strip() for part in _SENTENCE_SPLIT.split(source_text) if part.strip()]
    if not sentences and source_text:
        sentences = [source_text]

    if not sentences:
        source_text = title or "Deze oefentekst heeft geen broninhoud."
        sentences = [source_text]

    min_coverage = _min_sentence_coverage(level, strictness)
    max_sentence_words = _max_sentence_words(level, strictness)

    filtered: list[str] = []
    for sentence in sentences:
        if _sentence_coverage(sentence, allowed_words) < min_coverage:
            continue
        if max_sentence_words and len(sentence.split()) > max_sentence_words:
            # Keep the sentence intact if possible; if not, skip it rather than
            # creating ungrammatical word-count chunks.
            continue
        filtered.append(sentence)

    if not filtered:
        filtered = sentences[: min(4, len(sentences))]

    adapted_text = _clip_to_word_count_at_sentence_boundary(filtered, word_count)
    replacements, glossary = _build_glossary(adapted_text, allowed_words, word_metadata)

    summary = (
        f"Rule-based fallback for level {level}. "
        f"It filtered source sentences and explained {len(glossary)} words outside the selected level."
    )
    logger.info(
        "reading_rule_adaptation level=%s replacements=%s glossary=%s",
        level,
        len(replacements),
        len(glossary),
    )
    return RuleAdaptationResult(
        adapted_text=adapted_text,
        summary=summary,
        replacements=replacements,
        glossary=glossary,
    )
