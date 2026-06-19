from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import BASE_DIR, settings
from backend.app.db.session import session_scope
from backend.app.modules.rag.application.chunking_service import ChunkingService
from backend.app.modules.rag.application.document_parser_service import DocumentParserService
from backend.app.modules.rag.application.embedding_service import EmbeddingService
from backend.app.modules.rag.application.job_progress_cache import set_rag_job_progress
from backend.app.modules.rag.application.rag_policy_service import get_rag_policy_service
from backend.app.modules.rag.domain.enums import DocumentStatus, IngestionJobStatus, SourceType
from backend.app.modules.rag.domain.models import IngestionJob
from backend.app.modules.rag.domain.value_objects import AccessContext
from backend.app.modules.rag.infrastructure.file_storage_adapter import get_file_storage
from backend.app.modules.rag.application.retrieve_cache import invalidate_user_retrieve_cache
from backend.app.modules.rag.infrastructure.pgvector_adapter import get_vector_store
from backend.app.modules.rag.infrastructure.repositories import get_rag_repository
from backend.app.modules.rag.infrastructure.sqlalchemy_models import RagChunk

logger = logging.getLogger(__name__)


@dataclass
class IndexEnqueueResult:
    job: IngestionJob
    schedule: bool


class DocumentIngestionService:
    def __init__(
        self,
        *,
        parser: DocumentParserService | None = None,
        chunker: ChunkingService | None = None,
        embeddings: EmbeddingService | None = None,
    ) -> None:
        self._parser = parser or DocumentParserService()
        self._chunker = chunker or ChunkingService()
        self._embeddings = embeddings or EmbeddingService(
            allow_deterministic=settings.APP_ENV != "production"
        )
        self._repo = get_rag_repository()
        self._policy = get_rag_policy_service()
        self._storage = get_file_storage()

    async def upload_document(
        self,
        db: AsyncSession,
        *,
        access: AccessContext,
        filename: str,
        content_type: str,
        data: bytes,
        project_id: str | None = None,
        organization_id: str | None = None,
    ):
        if not settings.RAG_ENABLED:
            raise RuntimeError("RAG is disabled")

        ext = Path(filename).suffix.lower().lstrip(".")
        if ext not in settings.rag_allowed_file_types_list:
            raise ValueError(f"Unsupported file type: {ext}")
        if len(data) > settings.RAG_MAX_UPLOAD_BYTES:
            raise ValueError("File too large")

        if project_id and not await self._policy.can_access_project(
            db, user_id=access.user_id, project_id=project_id
        ):
            raise PermissionError("Not authorized for this project")

        storage_path = await self._storage.save_upload(
            user_id=access.user_id,
            filename=filename,
            data=data,
        )
        row = await self._repo.create_document(
            db,
            user_id=uuid.UUID(access.user_id),
            organization_id=uuid.UUID(organization_id) if organization_id else None,
            project_id=project_id,
            filename=Path(storage_path).name,
            original_filename=filename,
            content_type=content_type,
            storage_path=storage_path,
            source_type=SourceType.UPLOAD.value,
            metadata={"size_bytes": len(data), "extension": ext},
        )
        logger.info("rag_upload user_id=%s document_id=%s filename=%s", access.user_id, row.id, filename)
        return self._repo.to_document(row)

    async def enqueue_index_document(
        self,
        db: AsyncSession,
        *,
        access: AccessContext,
        document_id: str,
    ):
        if not settings.RAG_ENABLED:
            raise RuntimeError("RAG is disabled")

        doc_uuid = uuid.UUID(document_id)
        row = await self._repo.get_document(db, document_id=doc_uuid)
        if row is None:
            raise LookupError("Document not found")
        if not await self._policy.can_write_document(db, access=access, document=row):
            raise PermissionError("Forbidden")

        active = await self._repo.find_active_job_for_document(db, document_id=doc_uuid)
        if active is not None:
            return IndexEnqueueResult(job=self._repo.to_job(active), schedule=False)

        job = await self._repo.create_job(
            db,
            document_id=row.id,
            user_id=uuid.UUID(access.user_id),
            project_id=row.project_id,
        )
        logger.info(
            "rag_index_enqueued job_id=%s document_id=%s user_id=%s",
            job.id,
            document_id,
            access.user_id,
        )
        await set_rag_job_progress(
            str(job.id),
            status=IngestionJobStatus.PENDING.value,
            progress_stage=DocumentStatus.UPLOADED.value,
        )
        return IndexEnqueueResult(job=self._repo.to_job(job), schedule=True)

    async def execute_index_job(
        self,
        *,
        job_id: str,
        user_id: str,
        document_id: str,
        project_id: str | None,
    ) -> None:
        if not settings.RAG_ENABLED:
            raise RuntimeError("RAG is disabled")

        access = AccessContext(user_id=user_id, project_id=project_id)
        async with session_scope() as db:
            await self._run_index_job(
                db,
                access=access,
                job_id=job_id,
                document_id=document_id,
            )

    async def index_document(
        self,
        db: AsyncSession,
        *,
        access: AccessContext,
        document_id: str,
    ):
        """Enqueue indexing and return immediately with a pending job record."""
        result = await self.enqueue_index_document(
            db,
            access=access,
            document_id=document_id,
        )
        return result.job

    async def _run_index_job(
        self,
        db: AsyncSession,
        *,
        access: AccessContext,
        job_id: str,
        document_id: str,
    ):
        doc_uuid = uuid.UUID(document_id)
        row = await self._repo.get_document(db, document_id=doc_uuid)
        if row is None:
            raise LookupError("Document not found")

        job = await self._repo.get_job(db, uuid.UUID(job_id))
        if job is None:
            raise LookupError("Job not found")
        if not await self._policy.can_write_document(db, access=access, document=row):
            raise PermissionError("Forbidden")

        await self._repo.update_job(
            db, job, status=IngestionJobStatus.RUNNING, started=True
        )
        await self._publish_job_progress(job_id=job_id, job=job, document=row)

        try:
            await self._repo.update_document_status(db, row, DocumentStatus.PARSING)
            await self._publish_job_progress(job_id=job_id, job=job, document=row)
            abs_path = str(self._storage.resolve_path(row.storage_path))
            parsed = await self._parser.parse(
                abs_path,
                metadata={
                    "document_id": str(row.id),
                    "filename": row.original_filename,
                    "user_id": str(row.user_id),
                },
            )

            await self._repo.update_document_status(db, row, DocumentStatus.CHUNKING)
            await self._publish_job_progress(job_id=job_id, job=job, document=row)
            chunks = await self._chunker.chunk(
                parsed,
                document_id=str(row.id),
                user_id=str(row.user_id),
                organization_id=str(row.organization_id) if row.organization_id else None,
                project_id=row.project_id,
                filename=row.original_filename,
                source_type=row.source_type,
            )
            if not chunks:
                raise ValueError("No text extracted from document")

            await self._repo.update_document_status(db, row, DocumentStatus.EMBEDDING)
            await self._publish_job_progress(job_id=job_id, job=job, document=row)
            vectors = await self._embed_chunks_parallel([c.content for c in chunks])
            for chunk, vector in zip(chunks, vectors, strict=True):
                chunk.embedding = vector
                chunk.id = str(uuid.uuid4())

            store = get_vector_store(db)
            await store.delete_document(str(row.id), str(row.user_id))
            await store.upsert_chunks(chunks)

            await self._repo.update_document_status(db, row, DocumentStatus.INDEXED)
            await self._repo.update_job(
                db, job, status=IngestionJobStatus.COMPLETED, finished=True
            )
            await self._publish_job_progress(job_id=job_id, job=job, document=row)
            logger.info(
                "rag_indexed document_id=%s chunks=%s user_id=%s job_id=%s",
                row.id,
                len(chunks),
                access.user_id,
                job_id,
            )
            await invalidate_user_retrieve_cache(str(row.user_id))
            return self._repo.to_job(job)
        except Exception as exc:
            await self._repo.update_document_status(db, row, DocumentStatus.FAILED)
            await self._repo.update_job(
                db,
                job,
                status=IngestionJobStatus.FAILED,
                error_message=str(exc),
                finished=True,
            )
            await self._publish_job_progress(job_id=job_id, job=job, document=row)
            logger.exception("rag_index_failed document_id=%s job_id=%s", row.id, job_id)
            raise

    async def _publish_job_progress(
        self,
        *,
        job_id: str,
        job,
        document,
    ) -> None:
        await set_rag_job_progress(
            job_id,
            status=str(job.status),
            progress_stage=str(document.status),
            error_message=job.error_message,
        )

    async def _embed_chunks_parallel(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        batch_size = max(1, settings.RAG_EMBEDDING_BATCH_SIZE)
        concurrency = max(1, settings.RAG_EMBEDDING_BATCH_CONCURRENCY)
        batches = [texts[index : index + batch_size] for index in range(0, len(texts), batch_size)]
        semaphore = asyncio.Semaphore(concurrency)

        async def _embed_batch(batch: list[str]) -> list[list[float]]:
            async with semaphore:
                return await self._embeddings.embed_texts(batch)

        batch_vectors = await asyncio.gather(*[_embed_batch(batch) for batch in batches])
        return [vector for batch in batch_vectors for vector in batch]

    async def delete_document(
        self,
        db: AsyncSession,
        *,
        access: AccessContext,
        document_id: str,
    ) -> None:
        doc_uuid = uuid.UUID(document_id)
        row = await self._repo.get_document(db, document_id=doc_uuid)
        if row is None:
            raise LookupError("Document not found")
        if not await self._policy.can_write_document(db, access=access, document=row):
            raise PermissionError("Forbidden")

        store = get_vector_store(db)
        await store.delete_document(document_id, str(row.user_id))
        await self._repo.soft_delete_document(db, row)
        self._storage.delete_file(row.storage_path)
        await invalidate_user_retrieve_cache(str(row.user_id))

    async def list_chunks(
        self,
        db: AsyncSession,
        *,
        access: AccessContext,
        document_id: str,
    ) -> list[dict]:
        doc_uuid = uuid.UUID(document_id)
        row = await self._repo.get_document(db, document_id=doc_uuid)
        if row is None:
            raise LookupError("Document not found")
        if not await self._policy.can_read_document(db, access=access, document=row):
            raise PermissionError("Forbidden")

        chunks = (
            await db.execute(
                select(RagChunk)
                .where(RagChunk.document_id == doc_uuid)
                .order_by(RagChunk.chunk_index.asc())
            )
        ).scalars().all()
        return [
            {
                "id": str(c.id),
                "chunk_index": c.chunk_index,
                "content": c.content,
                "token_count": c.token_count,
                "metadata": c.metadata_json,
            }
            for c in chunks
        ]


_ingestion: DocumentIngestionService | None = None


def get_document_ingestion_service() -> DocumentIngestionService:
    global _ingestion
    if _ingestion is None:
        _ingestion = DocumentIngestionService()
    return _ingestion
