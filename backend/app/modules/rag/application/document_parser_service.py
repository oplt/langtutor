from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from backend.app.core.config import BASE_DIR
from backend.app.modules.rag.domain.models import ParsedDocument
from backend.app.modules.rag.infrastructure.langchain_document_loaders import load_documents_from_path

logger = logging.getLogger(__name__)


class DocumentParserService:
    async def parse(self, file_path: str, metadata: dict | None = None) -> list[ParsedDocument]:
        path = Path(file_path)
        if not path.is_absolute():
            path = BASE_DIR / file_path
        logger.info("rag_parse_start path=%s", path)
        docs = await asyncio.to_thread(load_documents_from_path, str(path), metadata=metadata)
        logger.info("rag_parse_done path=%s pages=%s", path, len(docs))
        return docs
