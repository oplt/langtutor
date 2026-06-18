from __future__ import annotations

import os

import pytest

from backend.app.modules.llm.base import LLMChatRequest, LLMMessage
from backend.app.modules.llm.service import create_task_client

pytestmark = pytest.mark.integration

RUN_LLM_EVAL = os.getenv("RUN_LLM_EVAL", "").strip() == "1"


@pytest.mark.skipif(not RUN_LLM_EVAL, reason="Set RUN_LLM_EVAL=1 to run live LLM smoke tests")
@pytest.mark.asyncio
async def test_live_llm_chat_smoke() -> None:
    client = await create_task_client("tutor_chat")
    response = await client.chat(
        LLMChatRequest(
            messages=[LLMMessage(role="user", content="Reply with exactly: pong")],
            max_tokens=16,
        )
    )
    assert response.content
    assert "pong" in response.content.lower()
