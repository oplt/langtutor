from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.modules.auth.dependencies import auth_error, get_current_user
from backend.app.modules.knowledge.dependencies import require_knowledge_admin
from backend.app.modules.knowledge.paths import resolve_ingest_paths
from backend.app.modules.knowledge.tasks import enqueue_knowledge_ingest
from backend.app.modules.knowledge.schemas import (
    KnowledgeBaseCreateIn,
    KnowledgeBaseOut,
    KnowledgeIngestIn,
    KnowledgeSearchIn,
    KnowledgeSearchOut,
    KnowledgeSourceOut,
)
from backend.app.deps import knowledge_service_dep
from backend.app.modules.knowledge.service import DEFAULT_SOURCES, KnowledgeService
from backend.app.modules.users.models import User

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("/bases")
async def list_bases(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
    service: KnowledgeService = Depends(knowledge_service_dep),
):
    bases = await service.list_bases(db)
    return {
        "bases": [
            KnowledgeBaseOut(
                id=str(kb.id),
                name=kb.name,
                description=kb.description,
                stats=kb.stats_json or {},
            )
            for kb in bases
        ]
    }


@router.post("/bases")
async def create_base(
    payload: KnowledgeBaseCreateIn,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_knowledge_admin),
    service: KnowledgeService = Depends(knowledge_service_dep),
):
    try:
        kb = await service.create_base(db, name=payload.name, description=payload.description)
        await db.commit()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return KnowledgeBaseOut(
        id=str(kb.id),
        name=kb.name,
        description=kb.description,
        stats=kb.stats_json or {},
    )


@router.post("/bases/{kb_name}/ingest-default")
async def ingest_default(
    kb_name: str,
    _admin: User = Depends(require_knowledge_admin),
):
    paths = [str(path) for path in DEFAULT_SOURCES]
    enqueue_knowledge_ingest(kb_name=kb_name, paths=paths)
    return {"status": "accepted", "kb_name": kb_name, "path_count": len(paths)}


@router.post("/bases/{kb_name}/ingest")
async def ingest_paths(
    kb_name: str,
    payload: KnowledgeIngestIn,
    _admin: User = Depends(require_knowledge_admin),
):
    try:
        paths = resolve_ingest_paths(payload.paths)
    except ValueError as exc:
        code = str(exc)
        message = "Invalid ingest path."
        if code.startswith("path_not_allowed:"):
            message = "Ingest paths must be under the configured knowledge files directory."
        elif code.startswith("path_not_found:"):
            message = "One or more ingest paths do not exist."
        elif code.startswith("path_not_file:"):
            message = "Ingest paths must point to files."
        elif code == "paths_required":
            message = "At least one ingest path is required."
        raise HTTPException(
            status_code=400,
            detail=auth_error("invalid_ingest_paths", message, details={"reason": code}),
        ) from exc

    enqueue_knowledge_ingest(
        kb_name=kb_name,
        paths=[str(path) for path in paths],
    )
    return {"status": "accepted", "kb_name": kb_name, "path_count": len(paths)}


@router.post("/search")
async def search(
    payload: KnowledgeSearchIn,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
    service: KnowledgeService = Depends(knowledge_service_dep),
):
    hits = await service.search(db, kb_name=payload.kb_name, query=payload.query, top_k=payload.top_k)
    return KnowledgeSearchOut(
        query=payload.query,
        kb_name=payload.kb_name,
        sources=[
            KnowledgeSourceOut(
                chunk_id=str(hit.chunk.id),
                score=hit.score,
                title=hit.chunk.title,
                source=hit.chunk.source,
                content=hit.chunk.content,
                metadata=hit.chunk.metadata_json or {},
            )
            for hit in hits
        ],
    )
