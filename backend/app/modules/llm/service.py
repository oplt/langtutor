from __future__ import annotations

from collections.abc import AsyncIterator

from backend.app.modules.llm.base import LLMChatRequest, LLMChatResponse, LLMMessage
from backend.app.core.config import settings
from backend.app.modules.llm.factory import config_from_env, config_from_profile, create_llm_client
from backend.app.modules.llm.task_client import LLMTaskClient
from backend.app.modules.llm.task_client_cache import (
    get_cached_task_client,
    set_cached_task_client,
)


async def create_task_client(task: str) -> LLMTaskClient:
    cached = get_cached_task_client(task)
    if cached is not None:
        return cached

    from backend.app.modules.ai.service import AISettingsService

    service = AISettingsService()
    try:
        profile = await service.resolve_task_profile(task)
        config = config_from_profile(profile)
    except ValueError:
        config = config_from_env()
    if task in {"tutor_chat", "chat"}:
        config = config.model_copy(
            update={"timeout_seconds": float(settings.LLM_TUTOR_TIMEOUT_SECONDS)}
        )
    client = LLMTaskClient(task=task, client=create_llm_client(config), config=config)
    set_cached_task_client(task, client)
    return client


class LLMService:
    async def for_task(self, task: str) -> LLMTaskClient:
        return await create_task_client(task)

    async def complete(
        self,
        task: str,
        messages: list[LLMMessage],
        *,
        model: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict] | None = None,
    ) -> LLMChatResponse:
        client = await self.for_task(task)
        return await client.chat(
            LLMChatRequest(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
            )
        )

    async def stream(
        self,
        task: str,
        messages: list[LLMMessage],
        *,
        model: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        client = await self.for_task(task)
        async for chunk in client.stream_chat(
            LLMChatRequest(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
        ):
            yield chunk


_llm_service: LLMService | None = None


def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
