from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from backend.app.core.config import settings
from backend.app.modules.reading.text_analyzer import CoverageResult, analyze_coverage

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class FailingSentence:
    index: int
    text: str
    coverage: CoverageResult

    @property
    def redacted_log_data(self) -> dict[str, object]:
        return {
            "index": self.index,
            "coverage": self.coverage.coverage_percent,
            "unknown": self.coverage.unknown_word_list,
            "words": self.coverage.total_words,
            "textHash": hashlib.sha256(self.text.encode("utf-8")).hexdigest()[:12],
        }


def target_coverage(strictness: str) -> float:
    values = {
        "natural": settings.READING_COVERAGE_RELAXED_PERCENT,
        "balanced": settings.READING_COVERAGE_BALANCED_PERCENT,
        "strict": settings.READING_COVERAGE_STRICT_PERCENT,
    }
    return float(values[strictness])


def split_sentences(text: str) -> list[str]:
    return [part.strip() for part in _SENTENCE_SPLIT.split(text or "") if part.strip()]


def failing_sentences(
    text: str,
    allowed: set[str],
    target: float,
    *,
    protected_terms: set[str],
    require_no_unknown: bool = True,
) -> list[FailingSentence]:
    failures: list[FailingSentence] = []
    for index, sentence in enumerate(split_sentences(text)):
        coverage = analyze_coverage(sentence, allowed, protected_terms=protected_terms)
        if coverage.coverage_percent < target or (require_no_unknown and coverage.unknown_words > 0):
            failures.append(FailingSentence(index=index, text=sentence, coverage=coverage))
    return failures


def merge_sentence_repairs(original: str, failures: list[FailingSentence], repaired_text: str) -> str:
    sentences = split_sentences(original)
    repairs = split_sentences(repaired_text)
    if len(repairs) != len(failures):
        return original
    for failure, repair in zip(failures, repairs, strict=True):
        sentences[failure.index] = repair
    return " ".join(sentences)
