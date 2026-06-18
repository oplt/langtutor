from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.modules.extensions.partners.models import PartnerChannel, PartnerMessageLog

DAILY_PROMPTS = [
    "Schrijf drie zinnen over wat je vandaag hebt gedaan.",
    "Noem vijf dingen in je keuken — in het Nederlands.",
    "Oefen de voltooid tegenwoordige tijd: beschrijf je ochtendroutine.",
    "Lees een korte nieuwsheadline en vat hem samen in één zin.",
]


class PartnersService:
    async def list_channels(
        self, db: AsyncSession, *, user_id: uuid.UUID
    ) -> list[PartnerChannel]:
        result = await db.execute(
            select(PartnerChannel)
            .where(PartnerChannel.user_id == user_id)
            .order_by(PartnerChannel.created_at.desc())
        )
        return list(result.scalars().all())

    async def register_channel(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        channel_type: str,
        external_id: str,
        daily_prompt_hour_utc: int = 8,
    ) -> PartnerChannel:
        channel_type = channel_type.strip().lower()
        if channel_type not in {"telegram", "whatsapp"}:
            raise ValueError("channel_type must be telegram or whatsapp")

        row = PartnerChannel(
            user_id=user_id,
            channel_type=channel_type,
            external_id=external_id.strip(),
            webhook_secret=secrets.token_urlsafe(24),
            daily_prompt_hour_utc=max(0, min(daily_prompt_hour_utc, 23)),
        )
        db.add(row)
        await db.flush()
        return row

    async def disable_channel(
        self, db: AsyncSession, *, user_id: uuid.UUID, channel_id: uuid.UUID
    ) -> bool:
        row = (
            await db.execute(
                select(PartnerChannel)
                .where(PartnerChannel.id == channel_id)
                .where(PartnerChannel.user_id == user_id)
            )
        ).scalar_one_or_none()
        if row is None:
            return False
        row.enabled = False
        await db.flush()
        return True

    async def send_daily_prompt(
        self, db: AsyncSession, *, channel: PartnerChannel
    ) -> dict[str, str]:
        import json
        from datetime import date

        idx = date.today().toordinal() % len(DAILY_PROMPTS)
        prompt = DAILY_PROMPTS[idx]
        payload = {
            "channel_type": channel.channel_type,
            "external_id": channel.external_id,
            "prompt": prompt,
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "status": "logged",
        }
        log = PartnerMessageLog(
            channel_id=channel.id,
            direction="outbound",
            payload_json=json.dumps(payload, ensure_ascii=False)[:4000],
        )
        db.add(log)
        await db.flush()
        return payload

    async def handle_webhook(
        self,
        db: AsyncSession,
        *,
        channel_type: str,
        secret: str,
        body: dict,
    ) -> dict[str, str]:
        import json

        row = (
            await db.execute(
                select(PartnerChannel)
                .where(PartnerChannel.channel_type == channel_type.strip().lower())
                .where(PartnerChannel.webhook_secret == secret)
                .where(PartnerChannel.enabled.is_(True))
            )
        ).scalar_one_or_none()
        if row is None:
            raise PermissionError("Invalid webhook secret or disabled channel")

        log = PartnerMessageLog(
            channel_id=row.id,
            direction="inbound",
            payload_json=json.dumps(body, ensure_ascii=False)[:4000],
        )
        db.add(log)
        await db.flush()
        return {"status": "accepted", "channel_id": str(row.id)}


_service: PartnersService | None = None


def get_partners_service() -> PartnersService:
    global _service
    if _service is None:
        _service = PartnersService()
    return _service
