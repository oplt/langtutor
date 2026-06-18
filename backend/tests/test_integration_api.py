from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import app

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json().get("ok") is True


@pytest.mark.asyncio
async def test_metrics_endpoint_exposes_llm_series() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/metrics")
    assert response.status_code == 200
    body = response.text
    assert "llm_calls_total" in body
    assert "llm_input_tokens_total" in body
