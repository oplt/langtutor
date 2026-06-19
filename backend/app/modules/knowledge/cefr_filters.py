"""CEFR-aware metadata filters for BM25 knowledge search."""

from __future__ import annotations

from backend.app.modules.learning.engine import LEVEL_DEFINITIONS


def rank_bounds_for_cefr(level: str | None) -> tuple[int, int] | None:
    if not level:
        return None
    normalized = level.strip().upper()
    for definition in LEVEL_DEFINITIONS:
        if str(definition["level"]) == normalized or getattr(definition["level"], "value", "") == normalized:
            return int(definition["rank_min"]), int(definition["rank_max"])
    return None


def chunk_matches_cefr(metadata: dict, *, cefr_level: str | None, pos: str | None = None) -> bool:
    bounds = rank_bounds_for_cefr(cefr_level)
    if bounds is None:
        return True
    rank_min, rank_max = bounds
    raw_rank = metadata.get("rank")
    if raw_rank is None:
        tagged_level = str(metadata.get("cefr_level") or "").strip().upper()
        if tagged_level and tagged_level == cefr_level.strip().upper():
            return True
        if metadata.get("skip_cefr_filter") is True:
            return True
        return False
    try:
        rank = int(raw_rank)
    except (TypeError, ValueError):
        return False
    if rank < rank_min or rank > rank_max:
        return False
    if pos:
        chunk_pos = str(metadata.get("pos") or "").lower()
        if chunk_pos and pos.lower() not in chunk_pos:
            return False
    return True
