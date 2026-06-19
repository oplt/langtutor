"""Load L3 memory text for agent turns without importing agent modules."""

from __future__ import annotations

import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.modules.memory.l3_cache import L3_MEMORY_BLOCK_KEY
from backend.app.modules.memory.service import get_memory_service

_SECTION = re.compile(r"^###\s+(.+)$", re.MULTILINE)


async def load_l3_memory_block(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    metadata: dict,
    query: str | None = None,
) -> str:
    cached = metadata.get(L3_MEMORY_BLOCK_KEY)
    if isinstance(cached, str) and not query:
        return cached.strip()

    capability = str(metadata.get("active_capability") or metadata.get("capability") or "")
    service = get_memory_service()
    if query and query.strip():
        text = await service.read_l3_for_query(
            db,
            user_id=user_id,
            query=query.strip(),
            capability=capability or None,
        )
    else:
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


async def warm_l3_memory_on_login(user_id: uuid.UUID) -> None:
    from backend.app.db.session import session_scope

    async with session_scope() as db:
        text = await get_memory_service().read_l3_concat(
            db,
            user_id=user_id,
            use_cache=False,
        )
    if text.strip():
        return
    from backend.app.modules.memory.tasks import enqueue_synthesize_l3

    await enqueue_synthesize_l3(user_id)
