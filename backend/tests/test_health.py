from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from backend.app.core.health import readiness_report


def test_readiness_report_ok_when_database_up() -> None:
    async def _run() -> None:
        with (
            patch("backend.app.core.health.check_database", new_callable=AsyncMock, return_value=True),
            patch("backend.app.core.health.check_redis", new_callable=AsyncMock, return_value=True),
            patch("backend.app.core.health.check_llm", new_callable=AsyncMock, return_value="configured"),
        ):
            report = await readiness_report()

        assert report["ok"] is True
        assert report["checks"]["database"] is True
        assert report["checks"]["redis"] is True
        assert report["checks"]["llm"] == "configured"

    asyncio.run(_run())


def test_readiness_report_not_ready_when_database_down() -> None:
    async def _run() -> None:
        with (
            patch("backend.app.core.health.check_database", new_callable=AsyncMock, return_value=False),
            patch("backend.app.core.health.check_redis", new_callable=AsyncMock, return_value=True),
            patch("backend.app.core.health.check_llm", new_callable=AsyncMock, return_value="configured"),
        ):
            report = await readiness_report()

        assert report["ok"] is False
        assert report["checks"]["database"] is False

    asyncio.run(_run())
