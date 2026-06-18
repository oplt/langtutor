from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.modules.users.models import User
from backend.app.db.session import get_db
from backend.app.modules.auth.dependencies import get_current_user
from backend.app.modules.memory.schemas import MemoryDocOut, MemoryL2FactIn, MemoryPreferenceIn
from backend.app.deps import memory_service_dep
from backend.app.modules.memory.service import MemoryService
from backend.app.modules.memory.tasks import enqueue_synthesize_l3
from backend.app.modules.memory.types import L2_SURFACES, L3_SLOTS

router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.get("/overview")
async def memory_overview(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: MemoryService = Depends(memory_service_dep),
):
    return await service.overview(db, user_id=user.id)


@router.get("/l3")
async def read_l3(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: MemoryService = Depends(memory_service_dep),
):
    text = await service.read_l3_concat(db, user_id=user.id)
    return {"content": text}


@router.get("/l3/{slot}", response_model=MemoryDocOut)
async def read_l3_slot(
    slot: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: MemoryService = Depends(memory_service_dep),
):
    if slot not in L3_SLOTS:
        raise HTTPException(status_code=404, detail="Unknown L3 slot")
    doc = await service.get_l3_slot(db, user_id=user.id, slot=slot)
    return MemoryDocOut(key=slot, content=doc["content"], entries=doc["entries"])


@router.get("/l2/{surface}", response_model=MemoryDocOut)
async def read_l2_surface(
    surface: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: MemoryService = Depends(memory_service_dep),
):
    if surface not in L2_SURFACES:
        raise HTTPException(status_code=404, detail="Unknown surface")
    doc = await service.get_l2(db, user_id=user.id, surface=surface)
    return MemoryDocOut(key=surface, content=doc["content"], entries=doc["entries"])


@router.post("/preferences")
async def write_preference(
    payload: MemoryPreferenceIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: MemoryService = Depends(memory_service_dep),
):
    try:
        entry = await service.write_preference(
            db,
            user_id=user.id,
            text=payload.text,
            op=payload.op,
            target_id=payload.target_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "entry": entry.to_dict()}


@router.post("/l2")
async def append_l2(
    payload: MemoryL2FactIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: MemoryService = Depends(memory_service_dep),
):
    try:
        entry = await service.append_l2_fact(
            db,
            user_id=user.id,
            surface=payload.surface,
            text=payload.text,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "entry": entry.to_dict()}


@router.post("/synthesize", status_code=status.HTTP_202_ACCEPTED)
async def synthesize_memory(
    user: User = Depends(get_current_user),
):
    scheduled = await enqueue_synthesize_l3(user.id)
    return {"ok": True, "scheduled": scheduled}


@router.get("/traces")
async def list_traces(
    surface: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from backend.app.modules.memory.repository import MemoryRepository

    repo = MemoryRepository()
    traces = await repo.list_traces(db, user_id=user.id, surface=surface, limit=limit)
    return {
        "items": [
            {
                "id": str(trace.id),
                "surface": trace.surface,
                "kind": trace.kind,
                "session_id": trace.session_id,
                "turn_id": trace.turn_id,
                "payload": trace.payload,
                "created_at": trace.created_at.isoformat() if trace.created_at else None,
            }
            for trace in traces
        ]
    }
