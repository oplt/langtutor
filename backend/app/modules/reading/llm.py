from __future__ import annotations

import json
import logging
import re
from typing import Any

from backend.app.modules.llm.base import LLMMessage
from backend.app.modules.llm.json_parse import LLMJsonParseError, extract_json_object, repair_json_prompt
from backend.app.modules.llm.service import get_llm_service
from backend.app.modules.prompt.assembler import build_task_system_prompt
from backend.app.modules.reading.schemas import SentenceTranslationOut, Strictness, TranslationMode
from backend.app.modules.reading.source_fetcher import FetchedArticle
from backend.app.modules.reading.vocabulary_adapter import adapt_text_with_rules

logger = logging.getLogger(__name__)


class ReadingGenerationError(Exception):
    pass


def _parse_json_object(raw: str) -> dict[str, Any]:
    try:
        return extract_json_object(raw)
    except LLMJsonParseError as exc:
        raise ReadingGenerationError(f"LLM response was not valid JSON: {exc}") from exc


def _build_user_prompt(
    *,
    level: int,
    max_frequency_rank: int,
    interest_area: str,
    word_count: int,
    strictness: Strictness,
    allowed_words: set[str],
    source: FetchedArticle,
    unknown_words_to_fix: list[str] | None = None,
    previous_text: str = "",
    sentences_to_repair: list[str] | None = None,
    length_to_fix: bool = False,
) -> str:
    protected = f"{source.title}, {source.publisher}".strip(", ")
    allowed_vocabulary = sorted(word for word in allowed_words if word and " " not in word)
    retry_block = ""
    minimum_words = max(1, round(word_count * 0.8))
    maximum_words = max(minimum_words, round(word_count * 1.15))
    if length_to_fix:
        retry_block = (
            "\nThe previous adapted text is too short. Rewrite the ENTIRE text, not only individual sentences. "
            f"Output between {minimum_words} and {maximum_words} Dutch words. "
            "Add clear explanations and restatements only when supported by source facts; do not invent facts.\n"
        )
        if unknown_words_to_fix:
            retry_block += (
                "Also replace these words outside the selected level: "
                f"{json.dumps(unknown_words_to_fix, ensure_ascii=False)}\n"
            )
        if previous_text:
            retry_block += f"Previous adapted text:\n{previous_text}\n"
    elif sentences_to_repair:
        retry_block = (
            "\nRepair ONLY the numbered sentences below. Return exactly the same number of "
            "sentences, in the same order, in adaptedText. Do not rewrite passing sentences.\n"
            f"Sentences: {json.dumps(sentences_to_repair, ensure_ascii=False)}\n"
        )
    elif unknown_words_to_fix:
        retry_block = (
            "\nThe previous attempt still used these words outside the selected level. "
            "Replace them when possible, unless they are names, places, dates, or essential topic terms:\n"
            f"{json.dumps(unknown_words_to_fix[:80], ensure_ascii=False)}\n"
        )
        if previous_text:
            retry_block += f"\nPrevious adapted text:\n{previous_text}\n"

    return (
        "You are a Dutch language-learning reading adaptation agent.\n"
        f"Rewrite the source material for a learner at frequency level {level} "
        f"(top {max_frequency_rank} Dutch words).\n\n"
        f"Interest area: {interest_area}\n"
        f"Required length: {minimum_words}-{maximum_words} Dutch words\n"
        f"Strictness: {strictness}\n\n"
        "Vocabulary control rules:\n"
        "1. Use short Dutch sentences. Every ordinary content word MUST be in ALLOWED_VOCABULARY. "
        "Inflected forms of listed words are allowed.\n"
        "2. Keep names, places, dates, organizations, and essential topic terms.\n"
        "3. Explain any kept difficult topic terms in the glossary.\n"
        "4. For strict mode, use shorter sentences and simpler words.\n"
        "5. Preserve facts from the source; do not invent new facts.\n"
        "6. Avoid rare vocabulary and unnecessary compound words.\n"
        "7. Preserve only necessary named entities. Replace difficult words with simpler alternatives.\n"
        "8. List difficult-word substitutions in replacements.\n"
        "9. Do not copy long passages verbatim; create an educational learner text.\n"
        f"Protected terms that may remain: {protected}\n"
        f"ALLOWED_VOCABULARY (cumulative through level {level}): "
        f"{json.dumps(allowed_vocabulary, ensure_ascii=False, separators=(',', ':'))}\n"
        f"{retry_block}\n"
        f"Source title: {source.title}\n"
        f"Source URL: {source.url}\n"
        f"Source publisher: {source.publisher}\n\n"
        f"Source text:\n{source.content}\n\n"
        "Return ONLY valid JSON with this exact shape:\n"
        "{\n"
        '  "title": "",\n'
        '  "adaptedText": "",\n'
        '  "summary": "",\n'
        '  "replacements": [{"original":"","replacement":"","reason":""}],\n'
        '  "glossary": [{"word":"","definition":"","exampleSentence":"","reasonKept":""}],\n'
        '  "quiz": [{"question":"","options":["","","",""],"answer":""}]\n'
        "}\n"
    )


def _template_fallback(
    *,
    source: FetchedArticle,
    level: int,
    word_count: int,
    strictness: Strictness,
    allowed_words: set[str],
    word_metadata: dict[str, dict[str, str]],
) -> dict[str, Any]:
    rule_result = adapt_text_with_rules(
        source_text=source.content or source.summary,
        allowed_words=allowed_words,
        word_metadata=word_metadata,
        level=level,
        word_count=word_count,
        strictness=strictness,
        title=source.title,
    )
    return {
        "title": source.title or f"Leestekst niveau {level}",
        "adaptedText": rule_result.adapted_text,
        "summary": rule_result.summary,
        "replacements": rule_result.replacements,
        "glossary": rule_result.glossary,
        "adaptationMode": "rules",
        "warnings": [
            "LLM adaptation was unavailable. A rule-based filter/glossary fallback was used instead.",
            "Configure an Ollama or hosted LLM model for higher-quality Dutch rephrasing.",
        ],
        "quiz": [
            {
                "question": "Waar gaat deze tekst vooral over?",
                "options": [
                    source.title[:80] or "Het onderwerp van de bron",
                    "Een recept",
                    "Een weerbericht",
                    "Een handleiding voor computers",
                ],
                "answer": source.title[:80] or "Het onderwerp van de bron",
            }
        ],
    }


async def adapt_reading_text(
    *,
    level: int,
    max_frequency_rank: int,
    interest_area: str,
    word_count: int,
    strictness: Strictness,
    allowed_words: set[str],
    word_metadata: dict[str, dict[str, str]],
    source: FetchedArticle,
    unknown_words_to_fix: list[str] | None = None,
    previous_text: str = "",
    sentences_to_repair: list[str] | None = None,
    length_to_fix: bool = False,
) -> dict[str, Any]:
    system = build_task_system_prompt(task="reading_generation", ui_language="en")
    user = _build_user_prompt(
        level=level,
        max_frequency_rank=max_frequency_rank,
        interest_area=interest_area,
        word_count=word_count,
        strictness=strictness,
        allowed_words=allowed_words,
        source=source,
        unknown_words_to_fix=unknown_words_to_fix,
        previous_text=previous_text,
        sentences_to_repair=sentences_to_repair,
        length_to_fix=length_to_fix,
    )
    messages = [
        LLMMessage(role="system", content=system),
        LLMMessage(role="user", content=user),
    ]
    try:
        llm = get_llm_service()
        response = await llm.complete(
            "reading_generation",
            messages,
            response_format="json",
            max_tokens=max(512, min(1800, word_count * 3)),
        )
        try:
            parsed = _parse_json_object(response.content)
            if not str(parsed.get("adaptedText", "")).strip():
                raise ReadingGenerationError("adaptedText missing from LLM response")
        except ReadingGenerationError as first_error:
            logger.info(
                "reading_generation_json_repair_started level=%s error=%s",
                level,
                first_error,
            )
            repair = await llm.complete(
                "reading_generation",
                [
                    *messages,
                    LLMMessage(
                        role="assistant",
                        content=response.content[:4000],
                    ),
                    LLMMessage(
                        role="user",
                        content=(
                            "Your previous response violated the required JSON schema. "
                            "Return the complete reading result again as one valid JSON object. "
                            "The adaptedText field must be present and non-empty. No markdown."
                        ),
                    ),
                ],
                response_format="json",
                max_tokens=max(512, min(1800, word_count * 3)),
            )
            parsed = _parse_json_object(repair.content)
            if not str(parsed.get("adaptedText", "")).strip():
                raise ReadingGenerationError("adaptedText missing after JSON repair")
        parsed["adaptationMode"] = "llm"
        parsed.setdefault("warnings", [])
        return parsed
    except Exception as exc:
        logger.warning(
            "reading_generation_llm_failed level=%s error_type=%s error=%s",
            level,
            type(exc).__name__,
            str(exc) or repr(exc),
            exc_info=True,
        )
        return _template_fallback(
            source=source,
            level=level,
            word_count=word_count,
            strictness=strictness,
            allowed_words=allowed_words,
            word_metadata=word_metadata,
        )


def _split_sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text or "") if part.strip()]


async def _complete_translation_json(
    *,
    task: str,
    prompt: str,
    json_shape_hint: str,
) -> dict[str, Any]:
    llm = get_llm_service()
    messages = [LLMMessage(role="user", content=prompt)]
    response = await llm.complete(
        task,
        messages,
        response_format="json",
    )
    try:
        return _parse_json_object(response.content)
    except ReadingGenerationError:
        repair_prompt = (
            f"{repair_json_prompt(response.content)}\n"
            f"Required JSON shape: {json_shape_hint}"
        )
        repair_response = await llm.complete(
            task,
            [LLMMessage(role="user", content=repair_prompt)],
            response_format="json",
        )
        return _parse_json_object(repair_response.content)


async def translate_adapted_text(
    *,
    text: str,
    mode: TranslationMode,
    source_language: str = "Dutch",
    target_language: str = "English",
) -> tuple[str | None, list[SentenceTranslationOut]]:
    if mode == "none" or not text.strip():
        return None, []

    if mode == "sentence_by_sentence":
        sentences = _split_sentences(text)
        payload = {
            "mode": "sentence_by_sentence",
            "sentences": sentences,
            "sourceLanguage": source_language,
            "targetLanguage": target_language,
        }
        prompt = (
            "Translate each Dutch sentence to English for a language learner. "
            "Return ONLY valid JSON with no markdown or commentary. "
            'Shape: {"translations":[{"sourceSentence":"","translatedSentence":""}]}\n'
            f"Input:\n{json.dumps(payload, ensure_ascii=False)}"
        )
        json_shape_hint = '{"translations":[{"sourceSentence":"","translatedSentence":""}]}'
    else:
        prompt = (
            f"Translate this {source_language} learner text to {target_language}. "
            "Return ONLY valid JSON with no markdown or commentary. "
            'Shape: {"translatedText":""}\n'
            f"Text:\n{text}"
        )
        json_shape_hint = '{"translatedText":""}'

    try:
        parsed = await _complete_translation_json(
            task="reading_translation",
            prompt=prompt,
            json_shape_hint=json_shape_hint,
        )
    except Exception as exc:
        logger.warning("reading_translation_failed error=%s", exc, exc_info=True)
        return None, []

    if mode == "sentence_by_sentence":
        rows: list[SentenceTranslationOut] = []
        for item in parsed.get("translations", []):
            if not isinstance(item, dict):
                continue
            rows.append(
                SentenceTranslationOut(
                    sourceSentence=str(item.get("sourceSentence", "")),
                    translatedSentence=str(item.get("translatedSentence", "")),
                )
            )
        return None, rows

    translated = str(parsed.get("translatedText", "")).strip() or None
    return translated, []
