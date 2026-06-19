from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.app.db.base import CEFRLevel
from backend.app.modules.content.file_mtime_cache import read_text_cached


PLAYBOOK_ROOT = (
    Path(__file__).resolve().parent / "playbooks"
)

_playbook_cache: dict[str, tuple[float, "Playbook"]] = {}


@dataclass(frozen=True)
class Playbook:
    level: CEFRLevel
    title: str
    content: str
    version: str
    updated_at: str | None
    meta: dict[str, Any]


def _compute_version(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]


def _parse_title(content: str) -> str:
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("# ") and len(line) > 2:
            return line[2:].strip()
    return "Tutor Playbook"


def _load_playbook(level: CEFRLevel) -> Playbook | None:
    path = PLAYBOOK_ROOT / level.value / "SKILL.md"
    if not path.exists():
        return None
    content = read_text_cached(path)
    title = _parse_title(content)
    version = _compute_version(content)
    stat = path.stat()
    updated_at = None if stat.st_mtime is None else datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
    return Playbook(
        level=level,
        title=title,
        content=content,
        version=version,
        updated_at=updated_at,
        meta={"path": str(path)},
    )


def get_playbook(level: CEFRLevel) -> Playbook:
    path = PLAYBOOK_ROOT / level.value / "SKILL.md"
    mtime = path.stat().st_mtime if path.exists() else 0.0
    cache_key = level.value
    cached = _playbook_cache.get(cache_key)
    if cached is not None and cached[0] == mtime:
        return cached[1]

    pb = _load_playbook(level)
    if pb is None:
        pb = _load_playbook(CEFRLevel.A1)
    if pb is None:
        raise FileNotFoundError("No tutor playbooks found")

    if path.exists():
        _playbook_cache[cache_key] = (mtime, pb)
    return pb


def list_playbooks() -> list[Playbook]:
    out: list[Playbook] = []
    for level in CEFRLevel:
        pb = _load_playbook(level)
        if pb is not None:
            out.append(pb)
    out.sort(key=lambda p: p.level.value)
    return out


def get_playbook_text(level: str | None) -> str:
    if not level:
        return get_playbook(CEFRLevel.A1).content
    try:
        cefr = CEFRLevel(str(level).upper())
    except ValueError:
        cefr = CEFRLevel.A1
    return get_playbook(cefr).content


def get_playbook_excerpt(level: str | None, *, max_chars: int = 1200) -> str:
    content = get_playbook_text(level)
    if len(content) <= max_chars:
        return content
    lines = content.splitlines()
    kept: list[str] = []
    used = 0
    for line in lines:
        next_len = used + len(line) + 1
        if next_len > max_chars and kept:
            break
        kept.append(line)
        used = next_len
    excerpt = "\n".join(kept).strip()
    if len(content) > len(excerpt):
        excerpt = f"{excerpt}\n\n[Playbook truncated — use tutor tools for deeper CEFR guidance.]"
    return excerpt


def reset_playbook_cache_for_tests() -> None:
    _playbook_cache.clear()
