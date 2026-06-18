from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from backend.app.modules.agent.chat.pipeline import ChatPipeline
from backend.app.modules.agent.core.context import AgentContext
from backend.app.modules.agent.core.stream_bus import StreamBus


def test_run_turn_prefetches_independent_reads_in_parallel() -> None:
    async def _run() -> None:
        pipeline = ChatPipeline()
        context = AgentContext(user_id="user-1", cefr_level="A1")
        bus = StreamBus()

        settings_mock = MagicMock(system_prompt="base")
        client_mock = MagicMock()

        with (
            patch(
                "backend.app.modules.agent.chat.pipeline.asyncio.gather",
                new_callable=AsyncMock,
                return_value=(settings_mock, client_mock, "memory block"),
            ) as gather,
            patch(
                "backend.app.modules.agent.chat.pipeline.asyncio.to_thread",
                new_callable=AsyncMock,
                return_value=("persona", "playbook"),
            ),
            patch(
                "backend.app.modules.agent.chat.pipeline.AgentLoopRunner"
            ) as runner_cls,
        ):
            runner_cls.return_value.run = AsyncMock(
                return_value=MagicMock(
                    paused=False,
                    messages=[],
                    pending_tool_call=None,
                    ask_user=None,
                )
            )
            await pipeline._run_turn(context, bus, AsyncMock())

        gather.assert_awaited_once()
        assert len(gather.await_args.args) == 3

    asyncio.run(_run())
