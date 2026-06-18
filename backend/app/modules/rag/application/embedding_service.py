from __future__ import annotations

import asyncio
import logging

from backend.app.modules.rag.infrastructure.langchain_embeddings import (
    DeterministicEmbeddingBackend,
    EmbeddingBackend,
    LangChainEmbeddingBackend,
    get_embedding_backend,
)


logger = logging.getLogger(__name__)
_EMBED_MAX_ATTEMPTS = 3


class EmbeddingService:
    def __init__(
        self,
        backend: EmbeddingBackend | None = None,
        *,
        allow_deterministic: bool = False,
    ) -> None:
        self._backend = backend
        self._allow_deterministic = allow_deterministic

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        backend = self._backend
        if backend is None:
            backend = get_embedding_backend(allow_deterministic=self._allow_deterministic)
        last_error: Exception | None = None
        for attempt in range(1, _EMBED_MAX_ATTEMPTS + 1):
            try:
                return await backend.embed_texts(texts)
            except Exception as exc:
                last_error = exc
                if attempt >= _EMBED_MAX_ATTEMPTS:
                    break
                delay = 0.4 * attempt
                logger.warning("embedding_retry attempt=%s delay=%s error=%s", attempt, delay, exc)
                await asyncio.sleep(delay)
        if self._allow_deterministic:
            fallback = DeterministicEmbeddingBackend()
            return await fallback.embed_texts(texts)
        assert last_error is not None
        raise last_error

    async def embed_query(self, query: str) -> list[float]:
        normalized = query.strip()
        if not normalized:
            return []

        from backend.app.modules.rag.application.embedding_cache import (
            get_cached_embedding,
            set_cached_embedding,
        )

        cached = await get_cached_embedding(normalized)
        if cached is not None:
            return cached

        vectors = await self.embed_texts([normalized])
        vector = vectors[0] if vectors else []
        if vector:
            await set_cached_embedding(normalized, vector)
        return vector
