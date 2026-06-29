from __future__ import annotations

import re
import unicodedata

# Normalize common straight/curly apostrophes found in Dutch text and OCR output.
_APOSTROPHE_VARIANTS = re.compile(r"['‘’`´ʼ]")
# Keep apostrophes and hyphens while stripping other punctuation for lookup.
_PUNCTUATION_EXCEPT_APOSTROPHE_HYPHEN = re.compile(r"[^\w\s\-']", re.UNICODE)
_WHITESPACE = re.compile(r"\s+")
_VARIANT_SPLIT_RE = re.compile(r"\s*(?:,|/|;|\bor\b|\ben\b)\s*", re.IGNORECASE)
_DUTCH_SUFFIXES = ("ingen", "ing", "heden", "heid", "elijk", "lijk", "baar", "isch", "ten", "en", "er", "e")


def normalize_word(value: str) -> str:
    """Normalize a word or short vocabulary expression for Dutch lookup.

    The function lowercases, normalizes Unicode, preserves Dutch apostrophes
    such as ``'t`` / ``z'n``, strips most punctuation, and collapses spaces.
    """
    if not value:
        return ""
    text = unicodedata.normalize("NFKC", str(value).strip().lower())
    text = _APOSTROPHE_VARIANTS.sub("'", text)
    text = _PUNCTUATION_EXCEPT_APOSTROPHE_HYPHEN.sub(" ", text)
    text = text.strip("- ")
    return _WHITESPACE.sub(" ", text).strip()


def normalize_token_for_lookup(value: str) -> str:
    """Token-level normalization used during coverage analysis.

    Handles common reduced Dutch forms without destroying apostrophes before
    lookup, e.g. ``'t`` -> ``het`` and ``'s`` -> ``s`` / following token context.
    """
    token = normalize_word(value)
    if not token:
        return ""

    if token in {"'t", "t'", "t"}:
        return "het"
    if token in {"'m", "m"}:
        return "hem"
    if token in {"'n", "n"}:
        return "een"
    if token in {"'s", "s"}:
        return "s"

    # Common possessive clitics: z'n, m'n.
    if token in {"z'n", "zijn"}:
        return "zijn"
    if token in {"m'n", "mijn"}:
        return "mijn"

    return token


def expand_word_variants(raw_word: str) -> list[str]:
    """Expand entries like ``mij, me`` or ``eind / einde`` into lookup terms.

    Frequency-list source files often store multiple variants in the same
    ``word`` field. This function keeps the original normalized phrase and
    also extracts comma/slash/semicolon variants so that token lookup works.
    """
    normalized = normalize_word(raw_word)
    if not normalized:
        return []

    variants: list[str] = []

    def add(value: str) -> None:
        value = normalize_word(value)
        if value and value not in variants:
            variants.append(value)

    add(normalized)

    # Remove parenthetical explanation fragments before variant splitting.
    without_parens = re.sub(r"\([^)]*\)", " ", str(raw_word))
    for part in _VARIANT_SPLIT_RE.split(without_parens):
        add(part)

    return variants


def find_allowed_form(value: str, allowed: set[str]) -> str | None:
    """Recognize a conservative inflected form of an allowed Dutch lemma."""
    normalized = normalize_token_for_lookup(value)
    if not normalized:
        return None
    if normalized in allowed:
        return normalized

    for suffix in _DUTCH_SUFFIXES:
        if len(normalized) < len(suffix) + 3 or not normalized.endswith(suffix):
            continue
        stem = normalized[: -len(suffix)]
        for candidate in (stem, f"{stem}en"):
            if candidate in allowed:
                return candidate
    return None
