from __future__ import annotations

import re
from dataclasses import dataclass

from backend.app.modules.reading.vocabulary_loader import is_stopword
from backend.app.modules.reading.vocabulary_normalizer import find_allowed_form, normalize_token_for_lookup, normalize_word

# Includes leading apostrophe forms such as 't and internal forms such as z'n.
_TOKEN_RE = re.compile(r"['‘’]?[A-Za-zÀ-ÖØ-öø-ÿ0-9]+(?:['‘’][A-Za-zÀ-ÖØ-öø-ÿ]+)?|[0-9]+(?:[./-][0-9]+)*")
_NUMBER_RE = re.compile(r"^[0-9]+(?:[./-][0-9]+)*$")
_SENTENCE_END_RE = re.compile(r"[.!?]\s*$")


@dataclass(frozen=True)
class TokenAnalysis:
    token: str
    normalized: str
    category: str
    sentence_start: bool = False


@dataclass(frozen=True)
class CoverageResult:
    total_words: int
    allowed_words: int
    unknown_words: int
    coverage_percent: float
    unknown_word_list: list[str]
    proper_noun_list: list[str]
    acronym_list: list[str]


def tokenize(text: str) -> list[str]:
    return [match.group(0) for match in _TOKEN_RE.finditer(text or "")]


def _token_context(text: str) -> list[tuple[str, bool]]:
    """Return tokens with a best-effort sentence-start flag."""
    results: list[tuple[str, bool]] = []
    sentence_start = True
    previous_end = 0
    for match in _TOKEN_RE.finditer(text or ""):
        between = text[previous_end : match.start()]
        if _SENTENCE_END_RE.search(between):
            sentence_start = True
        token = match.group(0)
        results.append((token, sentence_start))
        sentence_start = False
        previous_end = match.end()
    return results


_COUNTRIES_AND_PLACES = {
    "nederland", "belgië", "duitsland", "frankrijk", "spanje", "italië", "europa",
    "amsterdam", "rotterdam", "utrecht", "brussel", "vlaanderen",
}


def _looks_like_acronym(token: str) -> bool:
    letters = "".join(char for char in token if char.isalpha())
    return len(letters) >= 2 and letters.isupper()


def _looks_like_proper_noun(
    token: str,
    *,
    normalized: str,
    allowed: set[str],
    sentence_start: bool,
    protected: set[str],
) -> bool:
    if not token or not token[0].isalpha():
        return False
    if normalized in allowed or is_stopword(normalized):
        return False
    if normalized in protected or normalized in _COUNTRIES_AND_PLACES:
        return True
    # Sentence-initial capitals are normal grammar, not proof of a name.
    if sentence_start:
        return False
    return token[0].isupper()


def classify_token(
    token: str,
    allowed: set[str],
    *,
    sentence_start: bool = False,
    protected: set[str] | None = None,
) -> str:
    if not token or not token.strip():
        return "punctuation"
    if _NUMBER_RE.fullmatch(token):
        return "number"
    if _looks_like_acronym(token):
        return "acronym"

    normalized = normalize_token_for_lookup(token)
    if not normalized:
        return "punctuation"
    if is_stopword(normalized):
        return "stopword"
    if find_allowed_form(normalized, allowed):
        return "allowed"
    if _looks_like_proper_noun(
        token,
        normalized=normalized,
        allowed=allowed,
        sentence_start=sentence_start,
        protected=protected or set(),
    ):
        return "proper_noun"
    return "unknown"


def analyze_tokens(text: str, allowed: set[str], *, protected_terms: set[str] | None = None) -> list[TokenAnalysis]:
    protected = {
        normalize_token_for_lookup(token)
        for term in protected_terms or set()
        for token in tokenize(term)
        if normalize_token_for_lookup(token)
    }
    analyses: list[TokenAnalysis] = []
    for token, sentence_start in _token_context(text):
        normalized = normalize_token_for_lookup(token)
        analyses.append(
            TokenAnalysis(
                token=token,
                normalized=normalized,
                category=classify_token(token, allowed, sentence_start=sentence_start, protected=protected),
                sentence_start=sentence_start,
            )
        )
    return analyses


def analyze_coverage(
    text: str,
    allowed: set[str],
    *,
    protected_terms: set[str] | None = None,
    max_unknown_list: int = 40,
) -> CoverageResult:
    analyses = analyze_tokens(text, allowed, protected_terms=protected_terms)
    content = [
        item for item in analyses
        if item.category not in {"punctuation", "number", "proper_noun", "acronym"}
    ]
    proper_nouns = sorted({item.token for item in analyses if item.category == "proper_noun"})
    acronyms = sorted({item.token for item in analyses if item.category == "acronym"})
    total = len(content)
    if total == 0:
        return CoverageResult(
            total_words=0,
            allowed_words=0,
            unknown_words=0,
            coverage_percent=100.0,
            unknown_word_list=[],
            proper_noun_list=proper_nouns,
            acronym_list=acronyms,
        )

    allowed_count = 0
    unknown_set: set[str] = set()
    for item in content:
        if item.category in {"allowed", "stopword"}:
            allowed_count += 1
        elif item.category == "unknown" and item.normalized:
            unknown_set.add(normalize_word(item.normalized))

    unknown_count = total - allowed_count
    coverage = round((allowed_count / total) * 100, 2)
    return CoverageResult(
        total_words=total,
        allowed_words=allowed_count,
        unknown_words=unknown_count,
        coverage_percent=coverage,
        unknown_word_list=sorted(unknown_set)[:max_unknown_list],
        proper_noun_list=proper_nouns[:max_unknown_list],
        acronym_list=acronyms[:max_unknown_list],
    )


def count_words(text: str) -> int:
    return len([token for token in tokenize(text) if normalize_word(token)])
