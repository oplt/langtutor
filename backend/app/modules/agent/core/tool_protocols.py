"""Protocol interfaces for agent tool dependencies (test doubles / DI)."""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


class KnowledgeSearchService(Protocol):
    async def search(
        self,
        db: AsyncSession,
        *,
        kb_name: str,
        query: str,
        top_k: int = 5,
        cefr_level: str | None = None,
        pos: str | None = None,
        min_score: float = 0.0,
    ) -> list[Any]: ...


class MemoryReadService(Protocol):
    async def read_l3_concat(
        self,
        db: AsyncSession,
        *,
        user_id: UUID,
        capability: str | None = None,
        use_cache: bool = True,
    ) -> str: ...


class RagRetrievalService(Protocol):
    async def retrieve(
        self,
        db: AsyncSession,
        query: str,
        *,
        user_id: str,
        top_k: int = 5,
        project_id: str | None = None,
    ) -> list[Any]: ...
