from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.modules.rag.application.document_ingestion_service import DocumentIngestionService


def test_embed_chunks_parallel_batches_with_semaphore(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "backend.app.modules.rag.application.document_ingestion_service.settings.RAG_EMBEDDING_BATCH_SIZE",
        2,
    )
    monkeypatch.setattr(
        "backend.app.modules.rag.application.document_ingestion_service.settings.RAG_EMBEDDING_BATCH_CONCURRENCY",
        2,
    )

    async def _run() -> None:
        service = DocumentIngestionService()
        service._embeddings = MagicMock()
        service._embeddings.embed_texts = AsyncMock(
            side_effect=lambda batch: [[1.0, 2.0, 3.0] for _ in batch]
        )

        vectors = await service._embed_chunks_parallel(["a", "b", "c", "d", "e"])

        assert len(vectors) == 5
        assert service._embeddings.embed_texts.await_count == 3

    asyncio.run(_run())
