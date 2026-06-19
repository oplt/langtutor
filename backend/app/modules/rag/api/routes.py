from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.background import schedule_background
from backend.app.core.config import settings
from backend.app.modules.users.models import User
from backend.app.db.session import get_db
from backend.app.modules.auth.dependencies import get_current_user
from backend.app.modules.rag.api.schemas import (
    AskIn,
    AskOut,
    ChunkOut,
    CitationOut,
    DocumentOut,
    JobOut,
    QueryLogOut,
    RetrieveIn,
    RetrievedChunkOut,
)
from backend.app.deps import document_ingestion_dep
from backend.app.modules.rag.application.document_ingestion_service import DocumentIngestionService
from backend.app.modules.rag.application.indexing_tasks import run_rag_index_job
from backend.app.modules.rag.api.errors import rag_ask_http_exception
from backend.app.modules.rag.application.retrieval_service import RagAnswerService, RetrievalService
from backend.app.modules.rag.domain.value_objects import AccessContext, RetrievalFilters
from backend.app.modules.rag.infrastructure.repositories import get_rag_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rag", tags=["rag"])


def _job_out(job, *, progress_stage: str | None = None) -> JobOut:
    return JobOut(
        id=job.id,
        document_id=job.document_id,
        status=job.status.value,
        progress_stage=progress_stage,
        error_message=job.error_message,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


try:
    import multipart  # noqa: F401

    HAS_MULTIPART = True
except ImportError:
    HAS_MULTIPART = False


def _access(user: User, project_id: str | None = None) -> AccessContext:
    return AccessContext(user_id=str(user.id), project_id=project_id)


def _require_rag_enabled() -> None:
    if not settings.RAG_ENABLED:
        raise HTTPException(status_code=503, detail="Document RAG is disabled")


@router.get("/status")
async def rag_status(user: User = Depends(get_current_user)):
    _ = user
    return {"enabled": settings.RAG_ENABLED, "vector_backend": settings.RAG_VECTOR_BACKEND}


if HAS_MULTIPART:

    @router.post("/documents/upload", response_model=DocumentOut)
    async def upload_document(
        file: UploadFile = File(...),
        project_id: str | None = Form(default=None),
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        service: DocumentIngestionService = Depends(document_ingestion_dep),
    ):
        _require_rag_enabled()
        data = await file.read()
        try:
            doc = await service.upload_document(
                db,
                access=_access(user, project_id),
                filename=file.filename or "upload.bin",
                content_type=file.content_type or "application/octet-stream",
                data=data,
                project_id=project_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        return DocumentOut(
            id=doc.id,
            user_id=doc.user_id,
            organization_id=doc.organization_id,
            project_id=doc.project_id,
            filename=doc.filename,
            original_filename=doc.original_filename,
            content_type=doc.content_type,
            status=doc.status.value,
            source_type=str(doc.source_type),
            metadata=doc.metadata,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )
else:

    @router.post("/documents/upload")
    async def upload_document_unavailable():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Document upload requires python-multipart to be installed.",
        )


@router.get("/documents", response_model=list[DocumentOut])
async def list_documents(
    project_id: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_rag_enabled()
    repo = get_rag_repository()
    rows = await repo.list_documents(db, user_id=user.id, project_id=project_id)
    return [
        DocumentOut(
            id=str(row.id),
            user_id=str(row.user_id),
            organization_id=str(row.organization_id) if row.organization_id else None,
            project_id=row.project_id,
            filename=row.filename,
            original_filename=row.original_filename,
            content_type=row.content_type,
            status=row.status,
            source_type=row.source_type,
            metadata=row.metadata_json or {},
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


@router.get("/documents/{document_id}", response_model=DocumentOut)
async def get_document(
    document_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_rag_enabled()
    import uuid

    from backend.app.modules.rag.application.rag_policy_service import get_rag_policy_service

    repo = get_rag_repository()
    row = await repo.get_document(db, document_id=uuid.UUID(document_id))
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if not await get_rag_policy_service().can_read_document(
        db, access=_access(user, row.project_id), document=row
    ):
        raise HTTPException(status_code=403, detail="Forbidden")
    doc = repo.to_document(row)
    return DocumentOut(
        id=doc.id,
        user_id=doc.user_id,
        organization_id=doc.organization_id,
        project_id=doc.project_id,
        filename=doc.filename,
        original_filename=doc.original_filename,
        content_type=doc.content_type,
        status=doc.status.value,
        source_type=str(doc.source_type),
        metadata=doc.metadata,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: DocumentIngestionService = Depends(document_ingestion_dep),
):
    _require_rag_enabled()
    try:
        await service.delete_document(db, access=_access(user), document_id=document_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post(
    "/documents/{document_id}/index",
    response_model=JobOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def index_document(
    document_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: DocumentIngestionService = Depends(document_ingestion_dep),
):
    _require_rag_enabled()
    try:
        result = await service.enqueue_index_document(
            db, access=_access(user), document_id=document_id
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except Exception as exc:
        await db.rollback()
        logger.exception("rag_index_enqueue_failed document_id=%s", document_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    job = result.job
    if result.schedule:
        schedule_background(
            run_rag_index_job(
                job_id=job.id,
                user_id=str(user.id),
                document_id=document_id,
                project_id=job.project_id,
            ),
            name=f"rag_index:{job.id}",
        )
    doc_row = await get_rag_repository().get_document(db, document_id=uuid.UUID(document_id))
    return _job_out(job, progress_stage=doc_row.status if doc_row is not None else None)


@router.get("/documents/{document_id}/chunks", response_model=list[ChunkOut])
async def list_document_chunks(
    document_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: DocumentIngestionService = Depends(document_ingestion_dep),
):
    _require_rag_enabled()
    try:
        chunks = await service.list_chunks(
            db, access=_access(user), document_id=document_id
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return [ChunkOut(**chunk) for chunk in chunks]


@router.post("/retrieve", response_model=list[RetrievedChunkOut])
async def retrieve(
    payload: RetrieveIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_rag_enabled()
    service = RetrievalService()
    try:
        chunks = await service.retrieve(
            db,
            payload.query,
            access=_access(user, payload.project_id),
            top_k=payload.top_k,
            filters=RetrievalFilters(document_ids=payload.document_ids),
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return [
        RetrievedChunkOut(
            chunk_id=c.chunk_id,
            document_id=c.document_id,
            filename=c.filename,
            content=c.content,
            score=c.score,
            chunk_index=c.chunk_index,
            page_number=c.page_number,
        )
        for c in chunks
    ]


@router.post("/ask", response_model=AskOut)
async def ask(
    payload: AskIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_rag_enabled()
    service = RagAnswerService()
    try:
        result = await service.answer(
            db,
            payload.query,
            access=_access(user, payload.project_id),
            top_k=payload.top_k,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except Exception as exc:
        await db.rollback()
        logger.exception("rag_ask_failed user_id=%s", user.id)
        raise rag_ask_http_exception(exc) from exc
    return AskOut(
        query=result.query,
        answer=result.answer,
        citations=[CitationOut(**c.to_dict()) for c in result.citations],
        retrieved_chunk_ids=result.retrieved_chunk_ids,
        model_name=result.model_name,
        latency_ms=result.latency_ms,
        no_context=result.no_context,
    )


@router.get("/queries", response_model=list[QueryLogOut])
async def list_queries(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_rag_enabled()
    repo = get_rag_repository()
    rows = await repo.list_queries(db, user_id=user.id)
    return [
        QueryLogOut(
            id=str(row.id),
            query=row.query,
            answer=row.answer,
            model_name=row.model_name,
            latency_ms=row.latency_ms,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.get("/jobs/{job_id}", response_model=JobOut)
async def get_job(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_rag_enabled()
    repo = get_rag_repository()
    row = await repo.get_job(db, uuid.UUID(job_id))
    if row is None or str(row.user_id) != str(user.id):
        raise HTTPException(status_code=404, detail="Job not found")
    job = repo.to_job(row)
    doc_row = await repo.get_document(db, document_id=row.document_id)
    return _job_out(job, progress_stage=doc_row.status if doc_row is not None else None)
