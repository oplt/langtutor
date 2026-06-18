from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.modules.rag.domain.enums import DocumentStatus, IngestionJobStatus
from backend.app.modules.rag.domain.models import Document, IngestionJob, RagQuery
from backend.app.modules.rag.infrastructure.sqlalchemy_models import (
    RagDocument,
    RagIngestionJob,
    RagQueryLog,
)


class RagRepository:
    async def create_document(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        organization_id: uuid.UUID | None,
        project_id: str | None,
        filename: str,
        original_filename: str,
        content_type: str,
        storage_path: str,
        source_type: str,
        metadata: dict[str, Any],
    ) -> RagDocument:
        row = RagDocument(
            user_id=user_id,
            organization_id=organization_id,
            project_id=project_id,
            filename=filename,
            original_filename=original_filename,
            content_type=content_type,
            storage_path=storage_path,
            status=DocumentStatus.UPLOADED.value,
            source_type=source_type,
            metadata_json=metadata,
        )
        db.add(row)
        await db.flush()
        return row

    async def get_document(
        self, db: AsyncSession, *, document_id: uuid.UUID, include_deleted: bool = False
    ) -> RagDocument | None:
        stmt = select(RagDocument).where(RagDocument.id == document_id)
        if not include_deleted:
            stmt = stmt.where(RagDocument.deleted_at.is_(None))
        return (await db.execute(stmt)).scalar_one_or_none()

    async def list_documents(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        project_id: str | None = None,
    ) -> list[RagDocument]:
        stmt = (
            select(RagDocument)
            .where(RagDocument.user_id == user_id)
            .where(RagDocument.deleted_at.is_(None))
            .order_by(RagDocument.created_at.desc())
        )
        if project_id is not None:
            stmt = stmt.where(RagDocument.project_id == project_id)
        return list((await db.execute(stmt)).scalars().all())

    async def update_document_status(
        self, db: AsyncSession, row: RagDocument, status: DocumentStatus
    ) -> None:
        row.status = status.value
        await db.flush()

    async def soft_delete_document(self, db: AsyncSession, row: RagDocument) -> None:
        row.deleted_at = datetime.now(timezone.utc)
        row.status = DocumentStatus.DELETED.value
        await db.flush()

    async def create_job(
        self,
        db: AsyncSession,
        *,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        project_id: str | None,
    ) -> RagIngestionJob:
        row = RagIngestionJob(
            document_id=document_id,
            user_id=user_id,
            project_id=project_id,
            status=IngestionJobStatus.PENDING.value,
        )
        db.add(row)
        await db.flush()
        return row

    async def get_job(self, db: AsyncSession, job_id: uuid.UUID) -> RagIngestionJob | None:
        return (
            await db.execute(select(RagIngestionJob).where(RagIngestionJob.id == job_id))
        ).scalar_one_or_none()

    async def find_active_job_for_document(
        self, db: AsyncSession, *, document_id: uuid.UUID
    ) -> RagIngestionJob | None:
        stmt = (
            select(RagIngestionJob)
            .where(RagIngestionJob.document_id == document_id)
            .where(
                RagIngestionJob.status.in_(
                    [IngestionJobStatus.PENDING.value, IngestionJobStatus.RUNNING.value]
                )
            )
            .order_by(RagIngestionJob.created_at.desc())
            .limit(1)
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    async def update_job(
        self,
        db: AsyncSession,
        row: RagIngestionJob,
        *,
        status: IngestionJobStatus,
        error_message: str | None = None,
        started: bool = False,
        finished: bool = False,
    ) -> None:
        row.status = status.value
        if error_message is not None:
            row.error_message = error_message
        if started:
            row.started_at = datetime.now(timezone.utc)
        if finished:
            row.finished_at = datetime.now(timezone.utc)
        await db.flush()

    async def log_query(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        organization_id: uuid.UUID | None,
        project_id: str | None,
        query: str,
        answer: str,
        retrieved_chunk_ids: list[str],
        model_name: str,
        latency_ms: int,
    ) -> RagQueryLog:
        row = RagQueryLog(
            user_id=user_id,
            organization_id=organization_id,
            project_id=project_id,
            query=query,
            answer=answer,
            retrieved_chunk_ids_json=retrieved_chunk_ids,
            model_name=model_name,
            latency_ms=latency_ms,
        )
        db.add(row)
        await db.flush()
        return row

    async def list_queries(
        self, db: AsyncSession, *, user_id: uuid.UUID, limit: int = 50
    ) -> list[RagQueryLog]:
        stmt = (
            select(RagQueryLog)
            .where(RagQueryLog.user_id == user_id)
            .order_by(RagQueryLog.created_at.desc())
            .limit(limit)
        )
        return list((await db.execute(stmt)).scalars().all())

    @staticmethod
    def to_document(row: RagDocument) -> Document:
        return Document(
            id=str(row.id),
            user_id=str(row.user_id),
            organization_id=str(row.organization_id) if row.organization_id else None,
            project_id=row.project_id,
            filename=row.filename,
            original_filename=row.original_filename,
            content_type=row.content_type,
            storage_path=row.storage_path,
            status=DocumentStatus(row.status),
            source_type=row.source_type,  # type: ignore[arg-type]
            metadata=row.metadata_json or {},
            created_at=row.created_at,
            updated_at=row.updated_at,
            deleted_at=row.deleted_at,
        )

    @staticmethod
    def to_job(row: RagIngestionJob) -> IngestionJob:
        return IngestionJob(
            id=str(row.id),
            document_id=str(row.document_id),
            user_id=str(row.user_id),
            project_id=row.project_id,
            status=IngestionJobStatus(row.status),
            error_message=row.error_message,
            started_at=row.started_at,
            finished_at=row.finished_at,
            created_at=row.created_at,
        )

    @staticmethod
    def to_query(row: RagQueryLog) -> RagQuery:
        return RagQuery(
            id=str(row.id),
            user_id=str(row.user_id),
            organization_id=str(row.organization_id) if row.organization_id else None,
            project_id=row.project_id,
            query=row.query,
            answer=row.answer,
            retrieved_chunk_ids=list(row.retrieved_chunk_ids_json or []),
            model_name=row.model_name,
            latency_ms=row.latency_ms,
            created_at=row.created_at,
        )


_repository: RagRepository | None = None


def get_rag_repository() -> RagRepository:
    global _repository
    if _repository is None:
        _repository = RagRepository()
    return _repository
