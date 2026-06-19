from __future__ import annotations

import logging

from backend.app.db.session import session_scope
from backend.app.modules.knowledge.search_cache import get_knowledge_search_cache
from backend.app.modules.knowledge.service import get_knowledge_service
from backend.app.modules.learning.api import build_levels_payload
from backend.app.modules.learning.engine import ensure_words_seeded
from backend.app.modules.learning.response_cache import set_cached_levels

logger = logging.getLogger(__name__)


async def run_startup_warmup() -> None:
    """Seed learning corpus and default knowledge base off the request path."""
    try:
        kb_name = ""
        chunk_count = 0
        total_words = 0
        async with session_scope() as db:
            seeded = await ensure_words_seeded(db)
            if seeded:
                logger.info("startup_word_seed count=%s", seeded)
            kb = await get_knowledge_service().warmup_default_kb(db)
            kb_name = kb.name
            index = await get_knowledge_search_cache().load_index(db, kb)
            chunk_count = len(index.chunks)
            levels_payload = await build_levels_payload(db)
            total_words = int(levels_payload.get("total_words") or 0)
            await set_cached_levels(levels_payload)
        logger.info(
            "startup_knowledge_warm kb=%s chunks=%s levels=%s",
            kb_name,
            chunk_count,
            total_words,
        )
    except Exception:
        logger.exception("startup_warmup_failed")
