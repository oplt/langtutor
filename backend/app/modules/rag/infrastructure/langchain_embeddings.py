"""LangChain / provider embedding adapters — infrastructure only."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Protocol

import httpx

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

_OLLAMA_EMBED_CONCURRENCY = 8


class EmbeddingBackend(Protocol):
    async def embed_texts(self, texts: list[str]) -> list[list[float]]: ...


class LangChainEmbeddingBackend:
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        provider = settings.RAG_EMBEDDING_PROVIDER.lower()
        if provider == "openai":
            return await _embed_openai(texts)
        if provider == "ollama":
            return await _embed_ollama(texts)
        raise ValueError(f"Unsupported RAG embedding provider: {provider}")


async def _embed_openai(texts: list[str]) -> list[list[float]]:
    api_key = settings.embedding_api_key
    if not api_key:
        raise ValueError("RAG_EMBEDDING_API_KEY or LLM_API_KEY is required for OpenAI embeddings")

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": settings.RAG_EMBEDDING_MODEL, "input": texts},
        )
        response.raise_for_status()
        data = response.json()["data"]
        return [item["embedding"] for item in sorted(data, key=lambda x: x["index"])]


async def _embed_ollama(texts: list[str]) -> list[list[float]]:
    model = settings.RAG_EMBEDDING_MODEL or settings.LLM_MODEL
    base = settings.LLM_BASE_URL.rstrip("/")
    semaphore = asyncio.Semaphore(_OLLAMA_EMBED_CONCURRENCY)

    async with httpx.AsyncClient(timeout=60.0) as client:

        async def _embed_one(text: str) -> list[float]:
            async with semaphore:
                response = await client.post(
                    f"{base}/api/embeddings",
                    json={"model": model, "prompt": text},
                )
                response.raise_for_status()
                return response.json()["embedding"]

        return list(await asyncio.gather(*[_embed_one(text) for text in texts]))


class DeterministicEmbeddingBackend:
    """Test/dev fallback when external embedding APIs are unavailable."""

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        dim = settings.RAG_EMBEDDING_DIMENSION
        out: list[list[float]] = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            vec = []
            for i in range(dim):
                byte = digest[i % len(digest)]
                vec.append((byte / 255.0) * 2 - 1)
            out.append(vec)
        return out


def get_embedding_backend(*, allow_deterministic: bool = False) -> EmbeddingBackend:
    if allow_deterministic:
        return DeterministicEmbeddingBackend()
    return LangChainEmbeddingBackend()
