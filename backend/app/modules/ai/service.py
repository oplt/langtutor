from __future__ import annotations

import re
import secrets
import time
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from backend.app.core.config import settings as app_settings

from backend.app.modules.ai.schemas import (
    LLMConnectionTestRequest,
    LLMProfile,
    LLMProfileCreate,
    LLMProfilesResponse,
    LLMProfileUpdate,
    LLMProviderSettings,
    LLMRoutingSettings,
    LLMRoutingUpdate,
    LLMSettingsResponse,
    LLMSettingsUpdate,
    LLMTaskDefault,
)
from backend.app.modules.llm.base import LLMChatRequest, LLMProviderConfig
from backend.app.modules.llm.errors import LLMError
from backend.app.modules.llm.factory import config_from_profile, create_llm_client
from backend.app.modules.llm.provider_registry import PROVIDERS
from backend.app.modules.settings.repository import MASK, SettingsRepository

TASK_DEFAULTS: dict[str, LLMTaskDefault] = {
    "tutor_chat": LLMTaskDefault(provider="ollama"),
    "story_generation": LLMTaskDefault(provider="ollama"),
    "quiz_generation": LLMTaskDefault(provider="ollama"),
    "grammar_explanation": LLMTaskDefault(provider="ollama"),
    "correction": LLMTaskDefault(provider="openai"),
    "placement": LLMTaskDefault(provider="ollama"),
}

_public_settings_cache: tuple[float, LLMSettingsResponse] | None = None
_effective_settings_cache: tuple[float, LLMSettingsResponse] | None = None


def invalidate_llm_settings_cache() -> None:
    global _public_settings_cache, _effective_settings_cache
    _public_settings_cache = None
    _effective_settings_cache = None
    from backend.app.modules.llm.task_client_cache import invalidate_task_client_cache

    invalidate_task_client_cache()


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
        "profiles": [_default_llm_profile()],
        "default_profile_id": "ollama",
        "task_overrides": {},
    }


def _default_llm_profile() -> dict[str, Any]:
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


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or f"llm-{secrets.token_hex(4)}"


class AISettingsService:
    def __init__(self, repo: SettingsRepository | None = None) -> None:
        self.repo = repo or SettingsRepository()

    async def get_settings(self, *, effective: bool = False) -> LLMSettingsResponse:
        global _effective_settings_cache, _public_settings_cache

        now = time.monotonic()
        cache = _effective_settings_cache if effective else _public_settings_cache
        if cache is not None and now < cache[0]:
            return cache[1]

        doc = (
            await self.repo.get_effective_settings_doc()
            if effective
            else (await self.repo.get_settings_doc()).model_dump()
        )
        normalized = self._normalize_ai(doc.get("ai", {}), include_secret=effective)
        response = LLMSettingsResponse.model_validate(normalized)
        expires_at = now + app_settings.LLM_SETTINGS_CACHE_TTL_SECONDS
        if effective:
            _effective_settings_cache = (expires_at, response)
        else:
            _public_settings_cache = (expires_at, response)
        return response

    async def save_settings(self, payload: LLMSettingsUpdate) -> LLMSettingsResponse:
        public_doc = (await self.repo.get_settings_doc()).model_dump()
        normalized = self._normalize_ai(payload.model_dump(), include_secret=True)
        self._validate_settings(normalized)
        public_doc["ai"] = normalized
        await self.repo.put_settings_doc(public_doc)
        invalidate_llm_settings_cache()
        return await self.get_settings()

    async def list_profiles(self) -> LLMProfilesResponse:
        settings = await self.get_settings()
        return LLMProfilesResponse(
            profiles=settings.profiles,
            default_profile_id=settings.default_profile_id,
        )

    async def create_profile(self, payload: LLMProfileCreate) -> LLMProfile:
        settings = await self.get_settings(effective=True)
        profile_ids = {profile.id for profile in settings.profiles}
        profile_id = _slugify(payload.name)
        if profile_id in profile_ids:
            profile_id = f"{profile_id}-{secrets.token_hex(3)}"
        timestamp = _now_iso()
        profile = LLMProfile(
            id=profile_id,
            **payload.model_dump(),
            privacy_mode=self._privacy_for_provider(payload.provider),
            has_api_key=bool(payload.api_key),
            created_at=timestamp,
            updated_at=timestamp,
        )
        updated_profiles = [*settings.profiles, profile]
        default_profile_id = settings.default_profile_id or profile.id
        await self._save_profiles(updated_profiles, default_profile_id, settings.task_overrides)
        return await self.get_profile(profile.id)

    async def get_profile(self, profile_id: str, *, effective: bool = False) -> LLMProfile:
        settings = await self.get_settings(effective=effective)
        for profile in settings.profiles:
            if profile.id == profile_id:
                return profile
        raise ValueError(f"Unknown LLM profile: {profile_id}")

    async def update_profile(self, profile_id: str, payload: LLMProfileUpdate) -> LLMProfile:
        settings = await self.get_settings(effective=True)
        timestamp = _now_iso()
        updated: list[LLMProfile] = []
        found = False
        for profile in settings.profiles:
            if profile.id != profile_id:
                updated.append(profile)
                continue
            found = True
            raw = profile.model_dump()
            incoming = payload.model_dump()
            if not str(incoming.get("api_key") or "").strip():
                if profile.has_api_key or incoming.get("has_api_key"):
                    incoming["has_api_key"] = True
                    if profile.api_key:
                        incoming["api_key"] = MASK
            raw.update(incoming)
            raw["id"] = profile_id
            raw["privacy_mode"] = self._privacy_for_provider(str(raw.get("provider") or ""))
            raw["created_at"] = profile.created_at or timestamp
            raw["updated_at"] = timestamp
            updated.append(LLMProfile.model_validate(raw))
        if not found:
            raise ValueError(f"Unknown LLM profile: {profile_id}")
        await self._save_profiles(updated, settings.default_profile_id, settings.task_overrides)
        return await self.get_profile(profile_id)

    async def delete_profile(self, profile_id: str) -> None:
        settings = await self.get_settings(effective=True)
        updated = [profile for profile in settings.profiles if profile.id != profile_id]
        if len(updated) == len(settings.profiles):
            raise ValueError(f"Unknown LLM profile: {profile_id}")
        default_profile_id = settings.default_profile_id
        if default_profile_id == profile_id:
            default_profile_id = updated[0].id if updated else ""
        overrides = {
            task: routed_id
            for task, routed_id in settings.task_overrides.items()
            if routed_id != profile_id
        }
        await self._save_profiles(updated, default_profile_id, overrides)

    async def get_routing(self) -> LLMRoutingSettings:
        settings = await self.get_settings()
        return LLMRoutingSettings(
            default_profile_id=settings.default_profile_id,
            task_overrides=settings.task_overrides,
        )

    async def save_routing(self, payload: LLMRoutingUpdate) -> LLMRoutingSettings:
        settings = await self.get_settings(effective=True)
        profile_ids = {profile.id for profile in settings.profiles}
        if payload.default_profile_id and payload.default_profile_id not in profile_ids:
            raise ValueError("Default LLM profile does not exist.")
        for task, profile_id in payload.task_overrides.items():
            if task not in TASK_DEFAULTS:
                raise ValueError(f"Unsupported task: {task}")
            if profile_id and profile_id not in profile_ids:
                raise ValueError(f"Task route profile does not exist: {profile_id}")
        await self._save_profiles(
            settings.profiles,
            payload.default_profile_id,
            {task: value for task, value in payload.task_overrides.items() if value},
        )
        return await self.get_routing()

    async def resolve_task_profile(self, task: str) -> LLMProfile:
        settings = await self.get_settings(effective=True)
        profile_id = settings.task_overrides.get(task) or settings.default_profile_id
        if not profile_id and settings.profiles:
            profile_id = settings.profiles[0].id
        if not profile_id:
            raise ValueError("No LLM profile configured.")
        try:
            return await self.get_profile(profile_id, effective=True)
        except ValueError:
            for profile in settings.profiles:
                if profile.id != profile_id:
                    return await self.get_profile(profile.id, effective=True)
            raise

    async def list_profile_models(self, profile_id: str):
        profile = await self.get_profile(profile_id, effective=True)
        client = create_llm_client(config_from_profile(profile))
        return await client.list_models()

    async def test_profile(self, profile_id: str):
        profile = await self.get_profile(profile_id, effective=True)
        client = create_llm_client(config_from_profile(profile))
        return await client.health_check()

    async def list_models(self, provider: str):
        settings = await self.get_settings(effective=True)
        client = create_llm_client(self._client_config(provider, settings.providers[provider]))
        return await client.list_models()

    async def test_connection(self, request: LLMConnectionTestRequest):
        settings = await self.get_settings(effective=True)
        provider = request.provider or settings.active_provider
        provider_settings = request.settings or settings.providers.get(provider)
        if provider_settings is None:
            raise ValueError(f"Unknown LLM provider: {provider}")
        client = create_llm_client(self._client_config(provider, provider_settings))
        return await client.health_check()

    async def chat_test(self, request):
        settings = await self.get_settings(effective=True)
        provider = request.provider or settings.active_provider
        provider_settings = settings.providers.get(provider)
        if provider_settings is None:
            raise ValueError(f"Unknown LLM provider: {provider}")
        client = create_llm_client(self._client_config(provider, provider_settings))
        return await client.chat(
            LLMChatRequest(
                messages=request.messages,
                model=request.model or provider_settings.model,
                temperature=provider_settings.temperature,
                max_tokens=min(provider_settings.max_tokens, 256),
            )
        )

    async def _save_profiles(
        self,
        profiles: list[LLMProfile],
        default_profile_id: str,
        task_overrides: dict[str, str],
    ) -> None:
        doc = (await self.repo.get_settings_doc()).model_dump()
        ai = self._normalize_ai(doc.get("ai", {}), include_secret=False)
        ai["profiles"] = [profile.model_dump() for profile in profiles]
        ai["default_profile_id"] = default_profile_id
        ai["task_overrides"] = task_overrides
        doc["ai"] = ai
        await self.repo.put_settings_doc(doc)
        invalidate_llm_settings_cache()

    def _normalize_ai(self, raw: dict[str, Any], *, include_secret: bool) -> dict[str, Any]:
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
        profiles = self._normalize_profiles(source, merged, include_secret=include_secret)
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

    def _normalize_profiles(
        self,
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
                profile.privacy_mode = self._privacy_for_provider(profile.provider)
                if not include_secret:
                    profile.api_key = None
                profiles.append(profile)
        if profiles:
            return profiles
        timestamp = _now_iso()
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
                    privacy_mode=self._privacy_for_provider(provider_id),
                    created_at=timestamp,
                    updated_at=timestamp,
                )
            )
        return profiles

    def _validate_settings(self, data: dict[str, Any]) -> None:
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

    def _client_config(self, provider: str, settings: LLMProviderSettings) -> LLMProviderConfig:
        if provider not in PROVIDERS:
            raise ValueError(f"Unknown LLM provider: {provider}")
        api_base = settings.api_base or PROVIDERS[provider].default_api_base
        api_key = "" if settings.api_key == MASK else str(settings.api_key or "")
        return LLMProviderConfig(
            provider=provider,  # type: ignore[arg-type]
            api_base=api_base,
            api_key=api_key,
            model=settings.model,
            timeout_seconds=settings.timeout_seconds,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
            streaming=settings.streaming,
            vision=settings.vision,
            organization=settings.organization,
            project=settings.project,
            context_window=settings.context_window,
        )

    def _client_config_from_profile(self, profile: LLMProfile) -> LLMProviderConfig:
        return config_from_profile(profile)

    def _privacy_for_provider(self, provider: str) -> str:
        descriptor = PROVIDERS.get(provider)
        return "local" if descriptor and descriptor.mode == "local" else "cloud"


def llm_error_payload(exc: Exception) -> dict[str, Any]:
    if isinstance(exc, LLMError):
        return {"code": exc.code, "message": str(exc), "detail": exc.detail}
    return {"code": "LLM_REQUEST_FAILED", "message": str(exc), "detail": ""}
