from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.app.db.base import CEFRLevel


PLAYBOOK_ROOT = (
    Path(__file__).resolve().parent / "playbooks"
)


@dataclass(frozen=True)
class Playbook:
    level: CEFRLevel
    title: str
    content: str
    version: str
    updated_at: str | None
    meta: dict[str, Any]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


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
    content = _read_text(path)
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


@lru_cache(maxsize=64)
def get_playbook(level: CEFRLevel) -> Playbook:
    pb = _load_playbook(level)
    if pb is None:
        # Fallback to A1 if a level is missing.
        pb = _load_playbook(CEFRLevel.A1)
    if pb is None:
        raise FileNotFoundError("No tutor playbooks found")
    return pb


def list_playbooks() -> list[Playbook]:
    out: list[Playbook] = []
    for level in CEFRLevel:
        pb = _load_playbook(level)
        if pb is not None:
            out.append(pb)
    # Stable ordering.
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
