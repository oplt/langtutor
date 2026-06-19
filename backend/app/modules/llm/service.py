from __future__ import annotations

from collections.abc import AsyncIterator

from backend.app.modules.llm.base import LLMChatRequest, LLMChatResponse, LLMMessage
from backend.app.modules.llm.circuit_breaker import get_llm_circuit_breaker
from backend.app.modules.llm.errors import LLMProviderUnavailableError
from backend.app.modules.llm.factory import config_from_env, config_from_profile, create_llm_client
from backend.app.modules.llm.task_client import LLMTaskClient
from backend.app.modules.llm.timeouts import apply_task_timeout
from backend.app.modules.llm.task_client_cache import (
    get_cached_task_client,
    set_cached_task_client,
)


async def _profile_candidates(task: str) -> list:
    from backend.app.modules.ai.profile_resolution import resolve_profile_id_for_task
    from backend.app.modules.ai.service import AISettingsService

    service = AISettingsService()
    settings = await service.get_settings(effective=True)
    profile_ids = [profile.id for profile in settings.profiles if profile.enabled]
    if not profile_ids:
        return []

    primary_id = resolve_profile_id_for_task(
        task=task,
        default_profile_id=settings.default_profile_id,
        task_overrides=settings.task_overrides,
        profile_ids=set(profile_ids),
    )
    ordered = [primary_id] + [profile_id for profile_id in profile_ids if profile_id != primary_id]
    profiles = []
    seen: set[str] = set()
    for profile_id in ordered:
        if profile_id in seen:
            continue
        seen.add(profile_id)
        try:
            profiles.append(await service.get_profile(profile_id, effective=True))
        except ValueError:
            continue
    return profiles


async def create_task_client(task: str) -> LLMTaskClient:
    cached = get_cached_task_client(task)
    if cached is not None:
        return cached

    profiles = await _profile_candidates(task)
    last_error: Exception | None = None
    for profile in profiles:
        if not get_llm_circuit_breaker(profile.provider).allow():
            continue
        config = config_from_profile(profile)
        config = config.model_copy(
            update={"timeout_seconds": apply_task_timeout(task, config.timeout_seconds)}
        )
        client = LLMTaskClient(task=task, client=create_llm_client(config), config=config)
        set_cached_task_client(task, client)
        return client

    if profiles:
        profile = profiles[0]
        config = config_from_profile(profile)
        config = config.model_copy(
            update={"timeout_seconds": apply_task_timeout(task, config.timeout_seconds)}
        )
        client = LLMTaskClient(task=task, client=create_llm_client(config), config=config)
        set_cached_task_client(task, client)
        return client

    try:
        config = config_from_env()
    except Exception as exc:
        raise LLMProviderUnavailableError("No LLM profile configured.") from (last_error or exc)
    config = config.model_copy(
        update={"timeout_seconds": apply_task_timeout(task, config.timeout_seconds)}
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
