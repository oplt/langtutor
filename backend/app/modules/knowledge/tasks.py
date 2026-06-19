from __future__ import annotations

import logging
from pathlib import Path

from backend.app.core.background import schedule_background
from backend.app.db.session import session_scope
from backend.app.modules.knowledge.service import get_knowledge_service

logger = logging.getLogger(__name__)


async def run_knowledge_ingest(*, kb_name: str, paths: list[str]) -> dict[str, int]:
    resolved = [Path(path) for path in paths]
    async with session_scope() as db:
        result = await get_knowledge_service().ingest_paths(
            db,
            kb_name=kb_name,
            paths=resolved,
        )
    logger.info("knowledge_ingest_complete kb=%s inserted=%s", kb_name, result.get("inserted"))
    return {
        "inserted": int(result.get("inserted") or 0),
        "skipped": int(result.get("skipped") or 0),
    }


def enqueue_knowledge_ingest(*, kb_name: str, paths: list[str]) -> None:
    path_strings = [str(path) for path in paths]
    schedule_background(
        run_knowledge_ingest(kb_name=kb_name, paths=path_strings),
        name=f"knowledge_ingest:{kb_name}",
    )
    logger.info("knowledge_ingest_scheduled kb=%s paths=%s", kb_name, len(path_strings))
