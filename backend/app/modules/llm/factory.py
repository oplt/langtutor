from __future__ import annotations

from backend.app.core.config import settings
from backend.app.modules.ai.schemas import LLMProfile
from backend.app.modules.llm.anthropic import AnthropicClient
from backend.app.modules.llm.base import LLMProviderConfig
from backend.app.modules.llm.ollama import OllamaClient
from backend.app.modules.llm.openai_compatible import OpenAICompatibleClient
from backend.app.modules.llm.provider_registry import PROVIDERS, get_provider_spec
from backend.app.modules.llm.retry import RetryLLMClient


def create_llm_client(config: LLMProviderConfig, *, with_retry: bool = True):
    spec = get_provider_spec(config.provider)
    if spec.backend == "ollama":
        client = OllamaClient(config)
    elif spec.backend == "anthropic":
        client = AnthropicClient(config)
    else:
        client = OpenAICompatibleClient(config)
    if with_retry:
        return RetryLLMClient(client)
    return client


def config_from_profile(profile: LLMProfile) -> LLMProviderConfig:
    api_key = "" if profile.api_key in {None, "********"} else str(profile.api_key or "")
    model = (profile.model or "").strip() or settings.LLM_MODEL
    return LLMProviderConfig(
        provider=profile.provider,  # type: ignore[arg-type]
        api_base=profile.api_base or PROVIDERS[profile.provider].default_api_base,
        api_key=api_key,
        model=model,
        timeout_seconds=profile.timeout_seconds,
        temperature=profile.temperature,
        max_tokens=profile.max_tokens,
        streaming=profile.streaming,
        vision=profile.vision_support,
        context_window=profile.context_window,
    )


def config_from_env() -> LLMProviderConfig:
    provider = settings.LLM_PROVIDER if settings.LLM_PROVIDER in PROVIDERS else "ollama"
    return LLMProviderConfig(
        provider=provider,  # type: ignore[arg-type]
        api_base=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
        model=settings.LLM_MODEL,
        timeout_seconds=float(settings.LLM_TIMEOUT_SECONDS),
    )
