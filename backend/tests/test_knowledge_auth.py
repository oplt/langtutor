from __future__ import annotations

import asyncio

import pytest
from backend.app.core.config import BASE_DIR, settings
from backend.app.modules.knowledge.dependencies import require_knowledge_admin
from backend.app.modules.knowledge.paths import KNOWLEDGE_INGEST_ROOT, resolve_ingest_paths
from fastapi import HTTPException


def test_resolve_ingest_paths_rejects_outside_root() -> None:
    with pytest.raises(ValueError, match="path_not_allowed"):
        resolve_ingest_paths(["/etc/passwd"])


def test_resolve_ingest_paths_accepts_file_under_files_root() -> None:
    dutch_words = BASE_DIR / "files" / "dutchwordsordered.json"
    if not dutch_words.is_file():
        pytest.skip("dutchwordsordered.json not present in backend/files")
    resolved = resolve_ingest_paths([str(dutch_words)])
    assert resolved[0] == dutch_words.resolve()
    assert KNOWLEDGE_INGEST_ROOT in resolved[0].parents


def test_require_knowledge_admin_rejects_non_admin() -> None:
    class _User:
        email = "learner@example.com"

    with pytest.raises(HTTPException) as exc:
        asyncio.run(require_knowledge_admin(user=_User()))  # type: ignore[arg-type]
    assert exc.value.status_code == 403


def test_require_knowledge_admin_allows_listed_email(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "KNOWLEDGE_ADMIN_EMAILS", "admin@example.com")

    class _User:
        email = "admin@example.com"

    user = asyncio.run(require_knowledge_admin(user=_User()))  # type: ignore[arg-type]
    assert user.email == "admin@example.com"


def test_require_knowledge_admin_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "KNOWLEDGE_ADMIN_EMAILS", "")

    class _User:
        email = "admin@example.com"

    with pytest.raises(HTTPException) as exc:
        asyncio.run(require_knowledge_admin(user=_User()))  # type: ignore[arg-type]
    assert exc.value.status_code == 403
