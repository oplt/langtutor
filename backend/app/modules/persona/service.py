from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from backend.app.modules.content.file_mtime_cache import read_text_cached

PERSONA_ROOT = Path(__file__).resolve().parent / "personas"
PERSONA_FILE = "PERSONA.md"
DEFAULT_PERSONA = "conversation-partner"

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


@dataclass(frozen=True)
class PersonaInfo:
    name: str
    description: str
    source: str = "builtin"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "source": self.source,
        }


@dataclass(frozen=True)
class PersonaDetail:
    name: str
    description: str
    content: str
    source: str = "builtin"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "content": self.content,
            "source": self.source,
        }


class PersonaNotFoundError(Exception):
    pass


def _validate_name(name: str) -> str:
    candidate = (name or "").strip().lower()
    if not _NAME_RE.match(candidate):
        raise PersonaNotFoundError(candidate)
    return candidate


def _parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return {}, content
    try:
        data = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    return data, content[match.end() :]


def list_personas() -> list[PersonaInfo]:
    if not PERSONA_ROOT.exists():
        return []
    out: list[PersonaInfo] = []
    for entry in sorted(PERSONA_ROOT.iterdir()):
        if not entry.is_dir():
            continue
        path = entry / PERSONA_FILE
        if not path.exists():
            continue
        text = read_text_cached(path)
        meta, _ = _parse_frontmatter(text)
        out.append(
            PersonaInfo(
                name=entry.name,
                description=str(meta.get("description") or "").strip(),
            )
        )
    return out


def get_persona(name: str) -> PersonaDetail:
    slug = _validate_name(name)
    path = PERSONA_ROOT / slug / PERSONA_FILE
    if not path.exists():
        raise PersonaNotFoundError(slug)
    text = read_text_cached(path)
    meta, _ = _parse_frontmatter(text)
    return PersonaDetail(
        name=slug,
        description=str(meta.get("description") or "").strip(),
        content=text,
    )


def load_for_context(name: str | None) -> str:
    """Render persona block for system prompt injection."""
    slug = (name or DEFAULT_PERSONA).strip().lower()
    if not slug:
        return ""
    try:
        detail = get_persona(slug)
    except PersonaNotFoundError:
        if slug == DEFAULT_PERSONA:
            return ""
        try:
            detail = get_persona(DEFAULT_PERSONA)
        except PersonaNotFoundError:
            return ""
    _, body = _parse_frontmatter(detail.content)
    body = body.strip()
    if not body:
        return ""
    return (
        "## Active persona\n"
        "Embody the persona below for this entire conversation. "
        "It overrides generic style defaults.\n\n"
        f"### Persona: {detail.name}\n\n{body}"
    )


def resolve_persona_name(name: str | None) -> str:
    slug = (name or DEFAULT_PERSONA).strip().lower()
    try:
        _validate_name(slug)
        if (PERSONA_ROOT / slug / PERSONA_FILE).exists():
            return slug
    except PersonaNotFoundError:
        pass
    return DEFAULT_PERSONA
