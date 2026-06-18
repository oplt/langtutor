from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from backend.app.modules.rag.infrastructure import langchain_embeddings as embeddings_mod


def test_embed_ollama_runs_requests_in_parallel() -> None:
    async def _run() -> None:
        texts = ["a", "b", "c"]
        calls: list[str] = []

        class _FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict:
                return {"embedding": [0.1, 0.2]}

        mock_client = MagicMock()
        mock_client.post = AsyncMock(
            side_effect=lambda url, json: calls.append(json["prompt"]) or _FakeResponse()
        )

        class _ClientCtx:
            async def __aenter__(self):
                return mock_client

            async def __aexit__(self, *args):
                return False

        with patch.object(embeddings_mod.httpx, "AsyncClient", return_value=_ClientCtx()):
            result = await embeddings_mod._embed_ollama(texts)

        assert len(result) == len(texts)
        assert calls == texts

    asyncio.run(_run())
