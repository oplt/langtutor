from __future__ import annotations

from pathlib import Path

from backend.app.core.config import BASE_DIR

KNOWLEDGE_INGEST_ROOT = (BASE_DIR / "files").resolve()


def resolve_ingest_paths(paths: list[str]) -> list[Path]:
    """Resolve ingest paths and reject anything outside the knowledge files root."""
    if not paths:
        raise ValueError("paths_required")

    resolved: list[Path] = []
    for raw in paths:
        candidate = Path(raw).expanduser()
        if not candidate.is_absolute():
            candidate = (BASE_DIR / candidate).resolve()
        else:
            candidate = candidate.resolve()

        if KNOWLEDGE_INGEST_ROOT not in candidate.parents and candidate != KNOWLEDGE_INGEST_ROOT:
            raise ValueError(f"path_not_allowed:{raw}")
        if not candidate.exists():
            raise ValueError(f"path_not_found:{raw}")
        if not candidate.is_file():
            raise ValueError(f"path_not_file:{raw}")
        resolved.append(candidate)

    return resolved
