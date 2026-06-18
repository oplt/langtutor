from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from backend.app.modules.rag.application.document_ingestion_service import (
    DocumentIngestionService,
    IndexEnqueueResult,
)
from backend.app.modules.rag.domain.enums import DocumentStatus, IngestionJobStatus
from backend.app.modules.rag.domain.models import IngestionJob
from backend.app.modules.rag.domain.value_objects import AccessContext


def test_ingestion_job_status_values() -> None:
    assert IngestionJobStatus.PENDING.value == "pending"
    assert DocumentStatus.INDEXED.value == "indexed"


def test_enqueue_index_document_returns_existing_active_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "backend.app.modules.rag.application.document_ingestion_service.settings.RAG_ENABLED",
        True,
    )

    async def _run() -> None:
        service = DocumentIngestionService()
        access = AccessContext(user_id=str(uuid.uuid4()))
        document_id = str(uuid.uuid4())

        existing_job = IngestionJob(
            id=str(uuid.uuid4()),
            document_id=document_id,
            user_id=access.user_id,
            project_id=None,
            status=IngestionJobStatus.RUNNING,
        )

        service._repo = MagicMock()
        service._repo.get_document = AsyncMock(return_value=MagicMock(id=uuid.UUID(document_id)))
        service._repo.find_active_job_for_document = AsyncMock(return_value=MagicMock())
        service._repo.to_job = MagicMock(return_value=existing_job)
        service._policy = MagicMock()
        service._policy.can_write_document = AsyncMock(return_value=True)
        service._repo.create_job = AsyncMock()

        db = AsyncMock()
        result = await service.enqueue_index_document(db, access=access, document_id=document_id)

        assert isinstance(result, IndexEnqueueResult)
        assert result.schedule is False
        assert result.job.status == IngestionJobStatus.RUNNING
        service._repo.create_job.assert_not_called()

    asyncio.run(_run())


def test_enqueue_index_document_schedules_new_job(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "backend.app.modules.rag.application.document_ingestion_service.settings.RAG_ENABLED",
        True,
    )

    async def _run() -> None:
        service = DocumentIngestionService()
        access = AccessContext(user_id=str(uuid.uuid4()))
        document_id = str(uuid.uuid4())

        pending_job = IngestionJob(
            id=str(uuid.uuid4()),
            document_id=document_id,
            user_id=access.user_id,
            project_id="classroom:abc",
            status=IngestionJobStatus.PENDING,
        )

        service._repo = MagicMock()
        service._repo.get_document = AsyncMock(
            return_value=MagicMock(id=uuid.UUID(document_id), project_id="classroom:abc")
        )
        service._repo.find_active_job_for_document = AsyncMock(return_value=None)
        service._repo.create_job = AsyncMock(return_value=MagicMock())
        service._repo.to_job = MagicMock(return_value=pending_job)
        service._policy = MagicMock()
        service._policy.can_write_document = AsyncMock(return_value=True)

        db = AsyncMock()
        result = await service.enqueue_index_document(db, access=access, document_id=document_id)

        assert result.schedule is True
        assert result.job.project_id == "classroom:abc"
        service._repo.create_job.assert_awaited_once()

    asyncio.run(_run())
