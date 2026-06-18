from __future__ import annotations

import asyncio

from backend.app.core.background import schedule_background


def test_schedule_background_runs_coroutine() -> None:
    async def _run() -> None:
        ran = asyncio.Event()

        async def work() -> None:
            ran.set()

        schedule_background(work(), name="test-work")
        await asyncio.wait_for(ran.wait(), timeout=2.0)

    asyncio.run(_run())
