from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.exceptions import AppError
from backend.app.modules.reading.coverage_policy import failing_sentences, merge_sentence_repairs, target_coverage
from backend.app.modules.reading.generate_cache import PROMPT_VERSION, get_cached_reading_generate, set_cached_reading_generate
from backend.app.modules.reading.llm import adapt_reading_text
from backend.app.modules.reading.schemas import (
    LEVEL_MAX_RANK,
    ReadingCoverageOut,
    ReadingGenerateIn,
    ReadingGenerateOut,
    ReadingGlossaryEntryOut,
    ReadingQuizQuestionOut,
    ReadingReplacementOut,
    ReadingSaveOut,
    ReadingSourceOut,
)
from backend.app.modules.translation.service import get_translation_service
from backend.app.modules.reading.source_fetcher import fetch_source_material
from backend.app.modules.reading.text_analyzer import analyze_coverage, count_words
from backend.app.modules.reading.vocabulary_loader import load_cumulative_vocabulary

logger = logging.getLogger(__name__)

# Temporary fallback only. The save() method first tries a real DB model/table.
_saved_readings: dict[str, dict[str, Any]] = {}


def _coverage_to_schema(result) -> ReadingCoverageOut:
    return ReadingCoverageOut(
        totalWords=result.total_words,
        allowedWords=result.allowed_words,
        unknownWords=result.unknown_words,
        coveragePercent=result.coverage_percent,
        unknownWordList=result.unknown_word_list,
        properNouns=result.proper_noun_list,
        acronyms=result.acronym_list,
    )


def _model_name() -> str:
    for attr in ("LLM_MODEL", "OLLAMA_MODEL", "AI_MODEL", "OPENAI_MODEL"):
        value = getattr(settings, attr, "")
        if value:
            return str(value)
    return "default"


def _build_replacements(raw: list[Any]) -> list[ReadingReplacementOut]:
    result: list[ReadingReplacementOut] = []
    for item in raw or []:
        if not isinstance(item, dict) or not item.get("original"):
            continue
        result.append(
            ReadingReplacementOut(
                original=str(item.get("original", "")),
                replacement=str(item.get("replacement", "")),
                reason=str(item.get("reason", "")),
            )
        )
    return result


def _build_glossary(raw: list[Any]) -> list[ReadingGlossaryEntryOut]:
    result: list[ReadingGlossaryEntryOut] = []
    for item in raw or []:
        if not isinstance(item, dict) or not item.get("word"):
            continue
        definition = str(item.get("definition", item.get("meaning", "")))
        result.append(
            ReadingGlossaryEntryOut(
                word=str(item.get("word", "")),
                meaning=definition,
                definition=definition,
                exampleSentence=str(item.get("exampleSentence", item.get("example_sentence", ""))),
                reasonKept=str(item.get("reasonKept", item.get("reason_kept", "important topic word"))),
            )
        )
    return result


def _build_quiz(raw: list[Any]) -> list[ReadingQuizQuestionOut]:
    result: list[ReadingQuizQuestionOut] = []
    for item in raw or []:
        if not isinstance(item, dict) or not item.get("question"):
            continue
        options = [str(opt) for opt in item.get("options", []) if str(opt).strip()]
        if len(options) < 2:
            continue
        answer = str(item.get("answer", ""))
        result.append(
            ReadingQuizQuestionOut(
                type="multiple_choice",
                question=str(item.get("question", "")),
                options=options[:4],
                answer=answer,
            )
        )
    return result


CancelCheck = Callable[[], Awaitable[bool] | bool]


async def _is_cancelled(cancel_check: CancelCheck | None) -> bool:
    if cancel_check is None:
        return False
    result = cancel_check()
    if isinstance(result, Awaitable):
        return bool(await result)
    return bool(result)


async def _apply_deepl_translation(
    result: ReadingGenerateOut,
    *,
    translation_mode: str,
    context: str | None = None,
) -> ReadingGenerateOut:
    if translation_mode == "none":
        return result

    if result.translation and result.translation.status == "ok" and result.translation.text:
        return result

    translation_service = get_translation_service()
    translation, extra_warnings = await translation_service.translate_to_english(
        text=result.adapted_text,
        context=context,
    )
    warnings = [*result.warnings, *extra_warnings]
    return result.model_copy(
        update={
            "translation": translation,
            "translated_text": translation.text,
            "translation_mode": translation_mode,  # type: ignore[arg-type]
            "warnings": warnings,
        }
    )


class ReadingService:
    async def generate(
        self,
        payload: ReadingGenerateIn,
        *,
        cancel_check: CancelCheck | None = None,
    ) -> ReadingGenerateOut:
        level = payload.level
        max_rank = LEVEL_MAX_RANK[level]
        logger.info(
            "reading_generation_started level=%s interest=%s word_count=%s strictness=%s translation=%s",
            level,
            payload.interest_area,
            payload.word_count,
            payload.strictness,
            payload.translation_mode,
        )

        vocabulary = await load_cumulative_vocabulary(level)
        source = await fetch_source_material(
            interest_area=payload.interest_area,
            source_mode=payload.source_mode,
            word_count=payload.word_count,
        )

        target = target_coverage(payload.strictness)
        # A title contains ordinary content words, not only named entities.
        # Whitelisting every title token caused genuine difficult words to be
        # misclassified as proper nouns.
        protected_terms = {source.publisher}

        cached = await get_cached_reading_generate(
            level=level,
            interest_area=payload.interest_area,
            word_count=payload.word_count,
            source_mode=payload.source_mode,
            strictness=payload.strictness,
            source_title=source.title,
            source_url=source.url,
            source_published_at=source.published_at,
            source_content=source.content,
            language=payload.language,
            translation_mode=payload.translation_mode,
            model_name=_model_name(),
            prompt_version=PROMPT_VERSION,
        )
        if cached:
            try:
                cached_result = ReadingGenerateOut.model_validate(cached)
                logger.info(
                    "reading_generation_cache_hit level=%s coverage=%.2f target=%.2f fallback=%s",
                    level,
                    cached_result.coverage.coverage_percent,
                    target,
                    bool(cached_result.warning),
                )
                return await _apply_deepl_translation(
                    cached_result,
                    translation_mode=payload.translation_mode,
                    context=cached_result.source.title or cached_result.summary,
                )
            except Exception:
                logger.debug("reading_generate_cache_corrupt level=%s", level, exc_info=True)

        if await _is_cancelled(cancel_check):
            raise AppError(
                code="reading_generation_cancelled",
                message="Reading generation was cancelled.",
                status_code=409,
            )

        pre_coverage = analyze_coverage(
            source.content,
            vocabulary.allowed_words,
            protected_terms=protected_terms,
        )
        logger.info(
            "reading_pre_coverage level=%s coverage=%.2f unknown=%s",
            level,
            pre_coverage.coverage_percent,
            pre_coverage.unknown_words,
        )

        max_attempts = settings.READING_COVERAGE_MAX_ATTEMPTS if getattr(settings, "AI_AGENT_ENABLED", False) else 1
        llm_result: dict[str, Any] = {}
        post_coverage = None
        previous_text = ""
        best_text = ""
        best_coverage = None
        best_llm_result: dict[str, Any] = {}
        warnings: list[str] = []
        attempts_used = 0
        minimum_words = max(1, round(payload.word_count * 0.8))

        for attempt in range(1, max_attempts + 1):
            if await _is_cancelled(cancel_check):
                raise AppError(
                    code="reading_generation_cancelled",
                    message="Reading generation was cancelled.",
                    status_code=409,
                )
            attempts_used = attempt
            length_to_fix = bool(previous_text and count_words(previous_text) < minimum_words)
            failures = (
                failing_sentences(
                    previous_text,
                    vocabulary.allowed_words,
                    target,
                    protected_terms=protected_terms,
                )
                if previous_text and not length_to_fix else []
            )
            if failures:
                logger.info(
                    "reading_sentence_repair attempt=%s failures=%s",
                    attempt,
                    [item.redacted_log_data for item in failures[:5]],
                )
            if getattr(settings, "AI_AGENT_ENABLED", False):
                llm_result = await adapt_reading_text(
                    level=level,
                    max_frequency_rank=max_rank,
                    interest_area=payload.interest_area,
                    word_count=payload.word_count,
                    strictness=payload.strictness,
                    allowed_words=vocabulary.allowed_words,
                    word_metadata=vocabulary.word_metadata,
                    source=source,
                    unknown_words_to_fix=post_coverage.unknown_word_list if post_coverage else None,
                    previous_text=previous_text,
                    sentences_to_repair=[item.text for item in failures] if failures else None,
                    length_to_fix=length_to_fix,
                )
            else:
                from backend.app.modules.reading.llm import _template_fallback

                llm_result = _template_fallback(
                    source=source,
                    level=level,
                    word_count=payload.word_count,
                    strictness=payload.strictness,
                    allowed_words=vocabulary.allowed_words,
                    word_metadata=vocabulary.word_metadata,
                )

            generated_text = str(llm_result.get("adaptedText", "")).strip()
            adapted_text = (
                merge_sentence_repairs(previous_text, failures, generated_text)
                if previous_text and failures else generated_text
            )
            post_coverage = analyze_coverage(
                adapted_text,
                vocabulary.allowed_words,
                protected_terms=protected_terms,
            )
            previous_text = adapted_text
            logger.info(
                "reading_post_coverage attempt=%s level=%s coverage=%.2f target=%.2f unknown=%s",
                attempt,
                level,
                post_coverage.coverage_percent,
                target,
                post_coverage.unknown_words,
            )
            logger.info(
                "reading_coverage_terms attempt=%s unknown=%s proper_nouns=%s acronyms=%s",
                attempt,
                post_coverage.unknown_word_list,
                post_coverage.proper_noun_list,
                post_coverage.acronym_list,
            )
            candidate_words = count_words(adapted_text)
            best_words = count_words(best_text) if best_text else 0
            candidate_score = (
                -post_coverage.unknown_words,
                min(candidate_words, minimum_words),
                post_coverage.coverage_percent,
            )
            best_score = (
                -best_coverage.unknown_words,
                min(best_words, minimum_words),
                best_coverage.coverage_percent,
            ) if best_coverage is not None else None
            if best_score is None or candidate_score >= best_score:
                best_text = adapted_text
                best_coverage = post_coverage
                best_llm_result = llm_result
            # A selected vocabulary boundary is lexical, not an average. Even
            # one incidental unknown word must trigger repair. Proper nouns,
            # acronyms, numbers, and explicitly protected entities are already
            # excluded by the analyzer.
            if (
                post_coverage.unknown_words == 0
                and candidate_words >= minimum_words
            ) or llm_result.get("adaptationMode") != "llm":
                break

        assert best_coverage is not None
        post_coverage = best_coverage
        adapted_text = best_text
        llm_result = best_llm_result
        below_target = post_coverage.unknown_words > 0
        below_length = count_words(adapted_text) < minimum_words
        fallback_warning = "Text may be slightly above selected level" if below_target else None

        warnings.extend([str(item) for item in llm_result.get("warnings", []) if str(item).strip()])
        if fallback_warning:
            warnings.append(fallback_warning)
        if below_length:
            length_warning = (
                f"Text is shorter than requested ({count_words(adapted_text)} of about "
                f"{payload.word_count} words) because the source contained limited facts."
            )
            warnings.append(length_warning)
            fallback_warning = fallback_warning or length_warning

        source_title = str(llm_result.get("title", source.title))
        source_summary = str(llm_result.get("summary", ""))

        translation_out = None
        translated_text = None
        translation_warnings: list[str] = []
        if payload.translation_mode != "none":
            translation_service = get_translation_service()
            translation_out, translation_warnings = await translation_service.translate_to_english(
                text=adapted_text,
                context=source_title or source_summary,
            )
            translated_text = translation_out.text
        warnings.extend(translation_warnings)

        result = ReadingGenerateOut(
            adaptedText=adapted_text,
            translatedText=translated_text,
            translation=translation_out,
            sentenceTranslations=[],
            summary=source_summary,
            source=ReadingSourceOut(
                title=source_title,
                url=source.url,
                publisher=source.publisher,
                publishedAt=source.published_at,
            ),
            level=level,
            maxFrequencyRank=max_rank,
            wordCountRequested=payload.word_count,
            wordCountActual=count_words(adapted_text),
            coverage=_coverage_to_schema(post_coverage),
            preCoverage=_coverage_to_schema(pre_coverage),
            replacements=_build_replacements(llm_result.get("replacements", [])),
            glossary=_build_glossary(llm_result.get("glossary", [])),
            quiz=_build_quiz(llm_result.get("quiz", [])),
            sourceMode=payload.source_mode,
            strictness=payload.strictness,
            interestArea=payload.interest_area,
            translationMode=payload.translation_mode,
            adaptationMode=str(llm_result.get("adaptationMode", "raw")),
            warnings=warnings,
            targetCoveragePercent=target,
            unknownWords=post_coverage.unknown_word_list,
            attempts=attempts_used,
            warning=fallback_warning,
        )

        await set_cached_reading_generate(
            level=level,
            interest_area=payload.interest_area,
            word_count=payload.word_count,
            source_mode=payload.source_mode,
            strictness=payload.strictness,
            source_title=source.title,
            source_url=source.url,
            source_published_at=source.published_at,
            source_content=source.content,
            language=payload.language,
            translation_mode=payload.translation_mode,
            model_name=_model_name(),
            prompt_version=PROMPT_VERSION,
            payload=result.model_dump(mode="json", by_alias=True),
            ttl_seconds=(
                settings.READING_GENERATE_FALLBACK_CACHE_TTL_SECONDS
                if below_target or below_length else settings.READING_GENERATE_CACHE_TTL_SECONDS
            ),
        )
        logger.info("reading_generation_completed level=%s words=%s", level, result.word_count_actual)
        return result

    async def save(self, db: AsyncSession, *, user_id, payload: ReadingGenerateOut) -> ReadingSaveOut:
        reading_id = str(uuid.uuid4())
        saved_at = datetime.now(UTC)
        serialized = payload.model_dump(mode="json", by_alias=True)

        # Prefer a real SQLAlchemy model when the repository provides one.
        try:
            from backend.app.modules.reading.models import GeneratedReading  # type: ignore

            record = GeneratedReading(
                id=reading_id,
                user_id=user_id,
                language="nl",
                level=payload.level,
                max_frequency_rank=payload.max_frequency_rank,
                interest_area=payload.interest_area,
                requested_word_count=payload.word_count_requested,
                actual_word_count=payload.word_count_actual,
                source_title=payload.source.title,
                source_url=payload.source.url,
                source_publisher=payload.source.publisher,
                source_published_at=payload.source.published_at,
                adapted_text=payload.adapted_text,
                translated_text=payload.translated_text,
                summary=payload.summary,
                coverage_percent=payload.coverage.coverage_percent,
                unknown_words=payload.coverage.unknown_words,
                payload_json=serialized,
                created_at=saved_at,
            )
            db.add(record)
            await db.commit()
            return ReadingSaveOut(id=reading_id, savedAt=saved_at.isoformat())
        except Exception as exc:
            logger.warning("reading_save_db_failed_using_memory_fallback error=%s", exc, exc_info=True)
            try:
                await db.rollback()
            except Exception:
                pass

        _saved_readings[reading_id] = {
            "id": reading_id,
            "user_id": str(user_id),
            "payload": serialized,
            "saved_at": saved_at.isoformat(),
        }
        return ReadingSaveOut(id=reading_id, savedAt=_saved_readings[reading_id]["saved_at"])


_service: ReadingService | None = None


def get_reading_service() -> ReadingService:
    global _service
    if _service is None:
        _service = ReadingService()
    return _service
