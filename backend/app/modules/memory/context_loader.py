"""Load L3 memory text for agent turns without importing agent modules."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.modules.memory.l3_cache import L3_MEMORY_BLOCK_KEY
from backend.app.modules.memory.service import get_memory_service


async def load_l3_memory_block(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    metadata: dict,
) -> str:
    cached = metadata.get(L3_MEMORY_BLOCK_KEY)
    if isinstance(cached, str):
        return cached.strip()

    capability = str(metadata.get("active_capability") or metadata.get("capability") or "")
    service = get_memory_service()
    text = await service.read_l3_concat(
        db,
        user_id=user_id,
        capability=capability or None,
    )
    metadata[L3_MEMORY_BLOCK_KEY] = text
    if not text.strip():
        from backend.app.modules.memory.tasks import enqueue_synthesize_l3

        await enqueue_synthesize_l3(user_id)
    return text.strip()
