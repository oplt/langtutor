from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.app.modules.users.models import User
from backend.app.modules.auth.dependencies import get_current_user
from backend.app.modules.extensions.auto_router.service import classify_intent, resolve_capability

router = APIRouter(prefix="/api/extensions/auto", tags=["extensions-auto"])


class AutoRouteIn(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    capability: str | None = "auto"


class AutoRouteOut(BaseModel):
    capability: str
    reason: str
    confidence: float
    suggested_persona: str | None = None


@router.post("/route", response_model=AutoRouteOut)
async def route_capability(
    payload: AutoRouteIn,
    user: User = Depends(get_current_user),
):
    _ = user
    if payload.capability and payload.capability not in {"", "auto"}:
        return AutoRouteOut(
            capability=payload.capability,
            reason="Explicit capability requested by client.",
            confidence=1.0,
        )
    decision = classify_intent(payload.message)
    return AutoRouteOut(
        capability=decision.capability,
        reason=decision.reason,
        confidence=decision.confidence,
        suggested_persona=decision.suggested_persona,
    )


@router.get("/resolve")
async def preview_resolve(
    message: str,
    capability: str = "auto",
    user: User = Depends(get_current_user),
):
    _ = user
    resolved, metadata = resolve_capability(capability, message)
    return {"capability": resolved, "metadata": metadata}
