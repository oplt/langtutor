from __future__ import annotations

import os

# Configure env before any backend.app imports (Settings loads at import time).
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-at-least-32-chars!")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/languageapp_test",
)
os.environ.setdefault("KNOWLEDGE_ADMIN_EMAILS", "admin@example.com")
os.environ.setdefault("RAG_ENABLED", "false")


def pytest_configure(config: object) -> None:
    config.addinivalue_line("markers", "integration: integration tests (API/LLM smoke)")

