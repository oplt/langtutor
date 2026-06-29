from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import Any

from backend.app.core.config import BASE_DIR, settings
from backend.app.modules.learning.engine import STOPWORDS
from backend.app.modules.reading.schemas import LEVEL_MAX_RANK
from backend.app.modules.reading.vocabulary_normalizer import expand_word_variants, normalize_word

logger = logging.getLogger(__name__)

# Allow projects to override the vocabulary directory without editing code.
WORD_LEVELS_DIR = Path(
    getattr(settings, "READING_WORD_LEVELS_DIR", BASE_DIR.parent / "files" / "levels")
)

# Each level supports both naming conventions generated earlier in this project.
LEVEL_FILE_CANDIDATES: list[tuple[str, ...]] = [
    (
        "level_1_frequentieklasse_0_500.json",
    ),
    (
        "level_2_frequentieklasse_500_1000.json",
    ),
    (
        "level_3_frequentieklasse_1000_2000.json",
    ),
    (
        "level_4_frequentieklasse_2000_3000.json",

    ),
    (
        "level_5_frequentieklasse_3000_4000.json",

    ),
    (
        "level_6_frequentieklasse_4000_5000.json",

    ),
]


@dataclass(frozen=True)
class VocabularySnapshot:
    level: int
    max_frequency_rank: int
    allowed_words: set[str] = field(default_factory=set)
    word_metadata: dict[str, dict[str, str]] = field(default_factory=dict)


def _load_json_file(path: Path) -> list[dict[str, Any]]:
    raw = path.read_text(encoding="utf-8")
    payload = json.loads(raw)
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("words"), list):
        return [item for item in payload["words"] if isinstance(item, dict)]
    logger.warning("vocabulary_file_unsupported_shape path=%s", path)
    return []


def _resolve_level_file(index: int) -> Path | None:
    for filename in LEVEL_FILE_CANDIDATES[index]:
        path = WORD_LEVELS_DIR / filename
        if path.exists():
            return path
    return None


def _items_for_level(index: int) -> tuple[list[dict[str, Any]], Path | None]:
    path = _resolve_level_file(index)
    return (_load_json_file(path), path) if path else ([], None)


@lru_cache(maxsize=6)
def _load_level_files_cached(level: int) -> tuple[int, int, frozenset[str], MappingProxyType[str, dict[str, str]]]:
    max_rank = LEVEL_MAX_RANK.get(level, 2000)
    allowed: set[str] = set()
    metadata: dict[str, dict[str, str]] = {}
    missing_files: list[str] = []

    for index in range(level):
        items, path = _items_for_level(index)
        if path is None:
            missing_files.append(" | ".join(LEVEL_FILE_CANDIDATES[index]))
            continue

        logger.debug("vocabulary_file_loading level_index=%s path=%s", index + 1, path)
        for item in items:
            raw_word = str(item.get("word", "")).strip()
            if not raw_word:
                continue
            item_meta = {
                "translation": str(item.get("translation", "")).strip(),
                "grammatical_structure": str(item.get("grammatical_structure", "")).strip(),
            }
            for word in expand_word_variants(raw_word):
                normalized = normalize_word(word)
                if not normalized:
                    continue
                allowed.add(normalized)
                metadata.setdefault(normalized, item_meta)

    if missing_files:
        logger.warning(
            "vocabulary_files_missing dir=%s missing=%s",
            WORD_LEVELS_DIR,
            missing_files,
        )

    if not allowed:
        raise RuntimeError(
            f"No vocabulary words were loaded for level {level}. "
            f"Check READING_WORD_LEVELS_DIR/WORD_LEVELS_DIR: {WORD_LEVELS_DIR}"
        )

    frozen_metadata = MappingProxyType({key: dict(value) for key, value in metadata.items()})
    return level, max_rank, frozenset(allowed), frozen_metadata


def preload_reading_vocabulary_levels(levels: range | None = None) -> None:
    """Warm the in-process vocabulary cache at startup."""
    for level in levels or range(1, 7):
        _load_level_files_cached(level)


async def load_cumulative_vocabulary(level: int) -> VocabularySnapshot:
    clamped = max(1, min(6, int(level)))
    cached_level, max_rank, allowed, metadata = _load_level_files_cached(clamped)
    # Return mutable copies so downstream code cannot corrupt the lru_cache state.
    return VocabularySnapshot(
        level=cached_level,
        max_frequency_rank=max_rank,
        allowed_words=set(allowed),
        word_metadata={key: dict(value) for key, value in metadata.items()},
    )


def is_stopword(token: str) -> bool:
    return normalize_word(token) in STOPWORDS
