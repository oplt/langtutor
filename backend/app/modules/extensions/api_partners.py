from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.modules.users.models import User
from backend.app.db.session import get_db
from backend.app.modules.auth.dependencies import get_current_user
from backend.app.modules.extensions.partners.service import get_partners_service
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/extensions/partners", tags=["extensions-partners"])


class PartnerChannelIn(BaseModel):
    channel_type: str = Field(pattern=r"^(telegram|whatsapp)$")
    external_id: str = Field(min_length=1, max_length=255)
    daily_prompt_hour_utc: int = Field(default=8, ge=0, le=23)


@router.get("/channels")
async def list_channels(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = get_partners_service()
    rows = await service.list_channels(db, user_id=user.id)
    return [
        {
            "id": str(row.id),
            "channel_type": row.channel_type,
            "external_id": row.external_id,
            "enabled": row.enabled,
            "daily_prompt_hour_utc": row.daily_prompt_hour_utc,
            "webhook_url_hint": f"/api/extensions/partners/webhook/{row.channel_type}?secret={row.webhook_secret}",
        }
        for row in rows
    ]


@router.post("/channels")
async def register_channel(
    payload: PartnerChannelIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = get_partners_service()
    try:
        row = await service.register_channel(
            db,
            user_id=user.id,
            channel_type=payload.channel_type,
            external_id=payload.external_id,
            daily_prompt_hour_utc=payload.daily_prompt_hour_utc,
        )
        await db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "id": str(row.id),
        "channel_type": row.channel_type,
        "webhook_secret": row.webhook_secret,
    }


@router.delete("/channels/{channel_id}")
async def disable_channel(
    channel_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = get_partners_service()
    ok = await service.disable_channel(db, user_id=user.id, channel_id=channel_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Channel not found")
    await db.commit()
    return {"ok": True}


@router.post("/channels/{channel_id}/send-daily-prompt")
async def send_daily_prompt(
    channel_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = get_partners_service()
    channels = await service.list_channels(db, user_id=user.id)
    channel = next((c for c in channels if c.id == channel_id), None)
    if channel is None:
        raise HTTPException(status_code=404, detail="Channel not found")
    payload = await service.send_daily_prompt(db, channel=channel)
    await db.commit()
    return payload


@router.post("/webhook/{channel_type}")
async def partner_webhook(
    channel_type: str,
    secret: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    service = get_partners_service()
    try:
        result = await service.handle_webhook(
            db, channel_type=channel_type, secret=secret, body=body
        )
        await db.commit()
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return result
