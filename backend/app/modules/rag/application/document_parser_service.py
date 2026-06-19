from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from backend.app.core.config import BASE_DIR
from backend.app.modules.rag.domain.models import ParsedDocument
from backend.app.modules.rag.infrastructure.langchain_document_loaders import (
    load_documents_from_path,
    should_parse_in_process_pool,
)

logger = logging.getLogger(__name__)

_process_pool: ProcessPoolExecutor | None = None


def _get_process_pool() -> ProcessPoolExecutor:
    global _process_pool
    if _process_pool is None:
        _process_pool = ProcessPoolExecutor(max_workers=2)
    return _process_pool


class DocumentParserService:
    async def parse(self, file_path: str, metadata: dict | None = None) -> list[ParsedDocument]:
        path = Path(file_path)
        if not path.is_absolute():
            path = BASE_DIR / file_path
        logger.info("rag_parse_start path=%s", path)
        if should_parse_in_process_pool(path):
            loop = asyncio.get_running_loop()
            docs = await loop.run_in_executor(
                _get_process_pool(),
                load_documents_from_path,
                str(path),
                metadata,
            )
        else:
            docs = await asyncio.to_thread(load_documents_from_path, str(path), metadata=metadata)
        logger.info("rag_parse_done path=%s pages=%s", path, len(docs))
        return docs
