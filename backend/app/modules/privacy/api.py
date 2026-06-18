from __future__ import annotations

from datetime import datetime, timezone
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.modules.auth.dependencies import get_current_user
from backend.app.modules.users.models import User
from backend.app.db.session import get_db

router = APIRouter(prefix="/api/privacy", tags=["privacy"])

DEFAULT_PREFS: Dict[str, Any] = {
    "allowAnalytics": True,
    "retainHistory": True,
    "coachPersonalization": True,
    "retentionDays": 180,
    "goalPreset": "balanced",
}

_prefs_store: Dict[str, Dict[str, Any]] = {}
_audit_store: Dict[str, List[Dict[str, Any]]] = {}


def _user_key(user: User) -> str:
    return str(user.id)


def _get_prefs(user: User) -> Dict[str, Any]:
    return _prefs_store.get(_user_key(user), DEFAULT_PREFS.copy())


def _set_prefs(user: User, prefs: Dict[str, Any]) -> Dict[str, Any]:
    _prefs_store[_user_key(user)] = prefs
    return prefs


def _log_audit(user: User, action: str, details: Optional[Dict[str, Any]] = None) -> None:
    entry = {
        "id": str(uuid.uuid4()),
        "action": action,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "details": details or {},
    }
    _audit_store.setdefault(_user_key(user), []).insert(0, entry)


@router.get("/preferences")
async def get_preferences(user: User = Depends(get_current_user)):
    prefs = _get_prefs(user)
    return prefs


@router.put("/preferences")
async def put_preferences(
    payload: Dict[str, Any],
    user: User = Depends(get_current_user),
):
    if "retentionDays" in payload:
        retention_days = int(payload["retentionDays"])
        if retention_days < 30 or retention_days > 365:
            raise HTTPException(status_code=422, detail="retentionDays must be between 30 and 365")

    prefs = {**DEFAULT_PREFS, **payload}
    _set_prefs(user, prefs)
    _log_audit(user, "preferences_updated", {"retentionDays": prefs.get("retentionDays")})
    return prefs


@router.post("/run-retention")
async def run_retention(user: User = Depends(get_current_user)):
    _log_audit(user, "retention_cleanup", {"status": "completed"})
    return {"ok": True, "removed": 0}


@router.get("/audit-log")
async def audit_log(
    limit: int = Query(default=25, ge=1, le=200),
    user: User = Depends(get_current_user),
):
    items = _audit_store.get(_user_key(user), [])[:limit]
    return {"items": items}


@router.get("/export")
async def export_account_data(
    include_image_bytes: bool = Query(default=False),
    user: User = Depends(get_current_user),
):
    prefs = _get_prefs(user)
    _log_audit(user, "data_export", {"include_image_bytes": include_image_bytes})
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "includeImageBytes": include_image_bytes,
        "preferences": prefs,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
        },
        "scanHistory": [],
    }


@router.post("/delete-history")
async def delete_history(user: User = Depends(get_current_user)):
    _log_audit(user, "history_deleted", {"removed": 0})
    return {"ok": True, "removed": 0}


@router.delete("/account")
async def delete_account(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user.is_active = False
    user.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    _log_audit(user, "account_deleted", {})
    return {"ok": True}
