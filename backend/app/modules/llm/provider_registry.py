from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from backend.app.modules.ai.schemas import LLMProviderDescriptor

ProviderBackend = Literal["ollama", "openai_compat", "anthropic"]


@dataclass(frozen=True)
class ProviderSpec:
    descriptor: LLMProviderDescriptor
    backend: ProviderBackend


PROVIDER_REGISTRY: dict[str, ProviderSpec] = {
    "openai": ProviderSpec(
        descriptor=LLMProviderDescriptor(
            id="openai",
            label="OpenAI",
            mode="cloud",
            default_api_base="https://api.openai.com/v1",
            api_key_required=True,
            supports_vision=True,
        ),
        backend="openai_compat",
    ),
    "openai_compatible": ProviderSpec(
        descriptor=LLMProviderDescriptor(
            id="openai_compatible",
            label="OpenAI-compatible",
            mode="cloud",
            default_api_base="",
            api_key_required=False,
            supports_vision=True,
        ),
        backend="openai_compat",
    ),
    "openrouter": ProviderSpec(
        descriptor=LLMProviderDescriptor(
            id="openrouter",
            label="OpenRouter",
            mode="cloud",
            default_api_base="https://openrouter.ai/api/v1",
            api_key_required=True,
            supports_vision=True,
        ),
        backend="openai_compat",
    ),
    "ollama": ProviderSpec(
        descriptor=LLMProviderDescriptor(
            id="ollama",
            label="Ollama",
            mode="local",
            default_api_base="http://localhost:11434",
            supports_vision=True,
        ),
        backend="ollama",
    ),
    "llama_cpp": ProviderSpec(
        descriptor=LLMProviderDescriptor(
            id="llama_cpp",
            label="llama.cpp server",
            mode="local",
            default_api_base="http://127.0.0.1:8080/v1",
        ),
        backend="openai_compat",
    ),
    "huggingface": ProviderSpec(
        descriptor=LLMProviderDescriptor(
            id="huggingface",
            label="HuggingFace",
            mode="cloud",
            default_api_base="https://router.huggingface.co/v1",
            api_key_required=True,
            supports_vision=True,
        ),
        backend="openai_compat",
    ),
    "anthropic": ProviderSpec(
        descriptor=LLMProviderDescriptor(
            id="anthropic",
            label="Anthropic",
            mode="cloud",
            default_api_base="https://api.anthropic.com",
            api_key_required=True,
            supports_vision=True,
        ),
        backend="anthropic",
    ),
    "custom_http": ProviderSpec(
        descriptor=LLMProviderDescriptor(
            id="custom_http",
            label="Custom OpenAI-compatible",
            mode="custom",
            default_api_base="",
        ),
        backend="openai_compat",
    ),
}

PROVIDERS: dict[str, LLMProviderDescriptor] = {
    provider_id: spec.descriptor for provider_id, spec in PROVIDER_REGISTRY.items()
}

LLM_TASKS = (
    "tutor_chat",
    "story_generation",
    "quiz_generation",
    "grammar_explanation",
    "correction",
    "placement",
)


def get_provider_spec(provider_id: str) -> ProviderSpec:
    spec = PROVIDER_REGISTRY.get(provider_id)
    if spec is None:
        raise ValueError(f"Unknown LLM provider: {provider_id}")
    return spec
