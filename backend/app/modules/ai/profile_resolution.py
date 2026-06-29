from __future__ import annotations

import re
import secrets
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from backend.app.modules.ai.schemas import LLMProfile, LLMTaskDefault
from backend.app.modules.llm.provider_registry import PROVIDERS
from backend.app.modules.settings.repository import MASK

TASK_DEFAULTS: dict[str, LLMTaskDefault] = {
    "tutor_chat": LLMTaskDefault(provider="ollama"),
    "story_generation": LLMTaskDefault(provider="ollama"),
    "quiz_generation": LLMTaskDefault(provider="ollama"),
    "reading_generation": LLMTaskDefault(provider="ollama"),
    "reading_translation": LLMTaskDefault(provider="ollama"),
    "grammar_explanation": LLMTaskDefault(provider="ollama"),
    "correction": LLMTaskDefault(provider="openai"),
    "placement": LLMTaskDefault(provider="ollama"),
}


def default_llm_settings() -> dict[str, Any]:
    return {
        "active_provider": "ollama",
        "system_prompt": (
            "You are a supportive Dutch language tutor. Explain clearly, correct gently, "
            "and adapt to the learner's CEFR level."
        ),
        "providers": {
            provider_id: {
                "enabled": provider_id in {"ollama", "openai"},
                "api_base": descriptor.default_api_base,
                "model": "",
                "timeout_seconds": 120 if descriptor.mode == "local" else 60,
                "max_tokens": 2048,
                "temperature": 0.2,
                "streaming": descriptor.supports_streaming,
                "vision": descriptor.supports_vision,
                "context_window": 8192,
                "mode": "external_server",
                "server_binary_path": "",
                "model_path": "",
                "host": "127.0.0.1",
                "port": 8080,
                "gpu_layers": 0,
                "threads": 0,
                "batch_size": 512,
            }
            for provider_id, descriptor in PROVIDERS.items()
        },
        "task_defaults": {key: value.model_dump() for key, value in TASK_DEFAULTS.items()},
        "profiles": [default_llm_profile()],
        "default_profile_id": "ollama",
        "task_overrides": {},
    }


def default_llm_profile() -> dict[str, Any]:
    return {
        "id": "ollama",
        "name": "Local Ollama",
        "provider": "ollama",
        "api_base": "http://localhost:11434",
        "model": "",
        "enabled": True,
        "has_api_key": False,
        "api_key": None,
        "timeout_seconds": 120,
        "temperature": 0.2,
        "max_tokens": 2048,
        "context_window": 8192,
        "streaming": True,
        "vision_support": False,
        "privacy_mode": "local",
        "llama_connection_mode": "external_server",
        "llama_command": "",
        "llama_config": {
            "binary_path": "",
            "model_path": "",
            "host": "127.0.0.1",
            "port": 8080,
            "api_base": "http://127.0.0.1:8080/v1",
            "context_window": 8192,
            "gpu_layers": 0,
            "flash_attention": False,
            "parallel_slots": 1,
            "threads": 0,
            "batch_size": 512,
            "extra_allowed_args": [],
        },
    }


def slugify_profile_id(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or f"llm-{secrets.token_hex(4)}"


def privacy_for_provider(provider: str) -> str:
    descriptor = PROVIDERS.get(provider)
    return "local" if descriptor and descriptor.mode == "local" else "cloud"


def normalize_profiles(
    source: dict[str, Any],
    merged: dict[str, Any],
    *,
    include_secret: bool,
) -> list[LLMProfile]:
    raw_profiles = source.get("profiles")
    profiles: list[LLMProfile] = []
    if isinstance(raw_profiles, list):
        for raw_profile in raw_profiles:
            if not isinstance(raw_profile, dict):
                continue
            try:
                profile = LLMProfile.model_validate(raw_profile)
            except Exception:
                continue
            if profile.api_key == "":
                profile.has_api_key = False
            elif profile.api_key and profile.api_key != MASK:
                profile.has_api_key = True
            profile.privacy_mode = privacy_for_provider(profile.provider)
            if not include_secret:
                profile.api_key = None
            profiles.append(profile)
    if profiles:
        return profiles
    timestamp = datetime.now(UTC).isoformat()
    for provider_id, provider_settings in merged.get("providers", {}).items():
        if provider_id not in PROVIDERS or not isinstance(provider_settings, dict):
            continue
        if not provider_settings.get("enabled") and not provider_settings.get("model"):
            continue
        descriptor = PROVIDERS[provider_id]
        profiles.append(
            LLMProfile(
                id=provider_id,
                name=descriptor.label,
                provider=provider_id,
                api_base=str(provider_settings.get("api_base") or descriptor.default_api_base),
                model=str(provider_settings.get("model") or ""),
                enabled=bool(provider_settings.get("enabled", True)),
                has_api_key=bool(provider_settings.get("has_api_key")),
                api_key=provider_settings.get("api_key") if include_secret else None,
                timeout_seconds=float(provider_settings.get("timeout_seconds") or 60),
                temperature=float(provider_settings.get("temperature") or 0.2),
                max_tokens=int(provider_settings.get("max_tokens") or 2048),
                context_window=int(provider_settings.get("context_window") or 8192),
                streaming=bool(provider_settings.get("streaming", True)),
                vision_support=bool(provider_settings.get("vision", False)),
                privacy_mode=privacy_for_provider(provider_id),
                created_at=timestamp,
                updated_at=timestamp,
            )
        )
    return profiles


def normalize_ai_settings(raw: dict[str, Any], *, include_secret: bool) -> dict[str, Any]:
    defaults = default_llm_settings()
    source = deepcopy(raw or {})
    merged = deepcopy(defaults)
    merged.update({k: v for k, v in source.items() if k not in {"providers", "task_defaults"}})
    for provider_id, provider_settings in (source.get("providers") or {}).items():
        if provider_id in PROVIDERS and isinstance(provider_settings, dict):
            merged["providers"][provider_id].update(provider_settings)
    for task, task_default in (source.get("task_defaults") or {}).items():
        if task in TASK_DEFAULTS and isinstance(task_default, dict):
            merged["task_defaults"][task].update(task_default)
    profiles = normalize_profiles(source, merged, include_secret=include_secret)
    merged["profiles"] = [profile.model_dump() for profile in profiles]
    default_profile_id = str(source.get("default_profile_id") or "")
    if not default_profile_id and profiles:
        default_profile_id = profiles[0].id
    merged["default_profile_id"] = default_profile_id
    profile_ids = {profile.id for profile in profiles}
    merged["task_overrides"] = {
        task: profile_id
        for task, profile_id in (source.get("task_overrides") or {}).items()
        if task in TASK_DEFAULTS and profile_id in profile_ids
    }
    for provider_settings in merged["providers"].values():
        api_key = provider_settings.get("api_key")
        if api_key == "":
            provider_settings["has_api_key"] = False
        elif api_key and api_key != MASK:
            provider_settings["has_api_key"] = True
        if not include_secret:
            provider_settings["api_key"] = None
    active = str(merged.get("active_provider") or "ollama")
    merged["active_provider"] = active if active in PROVIDERS else "ollama"
    return merged


def validate_ai_settings(data: dict[str, Any]) -> None:
    active = data.get("active_provider")
    if active not in PROVIDERS:
        raise ValueError("Unsupported active LLM provider.")
    for provider_id, provider_settings in data.get("providers", {}).items():
        if provider_id not in PROVIDERS:
            raise ValueError(f"Unsupported LLM provider: {provider_id}")
        if provider_settings.get("enabled"):
            api_base = str(provider_settings.get("api_base") or "").strip()
            parsed = urlparse(api_base)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError(f"{provider_id} API base must be an absolute URL.")
    profile_ids = {profile.get("id") for profile in data.get("profiles", [])}
    default_profile_id = data.get("default_profile_id")
    if default_profile_id and default_profile_id not in profile_ids:
        raise ValueError("Default LLM profile does not exist.")


def resolve_profile_id_for_task(
    *,
    task: str,
    default_profile_id: str,
    task_overrides: dict[str, str],
    profile_ids: set[str],
) -> str:
    profile_id = task_overrides.get(task) or default_profile_id
    if not profile_id and profile_ids:
        profile_id = next(iter(profile_ids))
    if not profile_id:
        raise ValueError("No LLM profile configured.")
    if profile_id not in profile_ids and profile_ids:
        profile_id = next(iter(profile_ids))
    return profile_id
