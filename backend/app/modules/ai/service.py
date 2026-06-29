from __future__ import annotations

import secrets
import time
from datetime import UTC, datetime
from typing import Any

from backend.app.core.config import settings as app_settings

from backend.app.modules.ai.profile_resolution import (
    TASK_DEFAULTS,
    default_llm_profile,
    default_llm_settings,
    normalize_ai_settings,
    privacy_for_provider,
    resolve_profile_id_for_task,
    slugify_profile_id,
    validate_ai_settings,
)
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
)
from backend.app.modules.llm.base import LLMChatRequest, LLMProviderConfig
from backend.app.modules.llm.errors import LLMError
from backend.app.modules.llm.factory import config_from_profile, create_llm_client
from backend.app.modules.llm.provider_registry import PROVIDERS
from backend.app.modules.settings.repository import MASK, SettingsRepository

_public_settings_cache: tuple[float, LLMSettingsResponse] | None = None
_effective_settings_cache: tuple[float, LLMSettingsResponse] | None = None


def invalidate_llm_settings_cache() -> None:
    global _public_settings_cache, _effective_settings_cache
    _public_settings_cache = None
    _effective_settings_cache = None
    from backend.app.modules.llm.task_client_cache import invalidate_task_client_cache

    invalidate_task_client_cache()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


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
        normalized = normalize_ai_settings(doc.get("ai", {}), include_secret=effective)
        response = LLMSettingsResponse.model_validate(normalized)
        expires_at = now + app_settings.LLM_SETTINGS_CACHE_TTL_SECONDS
        if effective:
            _effective_settings_cache = (expires_at, response)
        else:
            _public_settings_cache = (expires_at, response)
        return response

    async def save_settings(self, payload: LLMSettingsUpdate) -> LLMSettingsResponse:
        public_doc = (await self.repo.get_settings_doc()).model_dump()
        normalized = normalize_ai_settings(payload.model_dump(), include_secret=True)
        validate_ai_settings(normalized)
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
        profile_id = slugify_profile_id(payload.name)
        if profile_id in profile_ids:
            profile_id = f"{profile_id}-{secrets.token_hex(3)}"
        timestamp = _now_iso()
        profile = LLMProfile(
            id=profile_id,
            **payload.model_dump(),
            privacy_mode=privacy_for_provider(payload.provider),
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
            raw["privacy_mode"] = privacy_for_provider(str(raw.get("provider") or ""))
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
        profile_ids = {profile.id for profile in settings.profiles}
        profile_id = resolve_profile_id_for_task(
            task=task,
            default_profile_id=settings.default_profile_id,
            task_overrides=settings.task_overrides,
            profile_ids=profile_ids,
        )
        try:
            return await self.get_profile(profile_id, effective=True)
        except ValueError:
            for profile in settings.profiles:
                if profile.id != profile_id:
                    return await self.get_profile(profile.id, effective=True)
            raise

    async def list_profile_models(self, profile_id: str, *, api_base: str | None = None):
        profile = await self.get_profile(profile_id, effective=True)
        if api_base and api_base.strip():
            profile = profile.model_copy(update={"api_base": api_base.strip()})
        client = create_llm_client(config_from_profile(profile))
        return await client.list_models()

    async def test_profile(self, profile_id: str):
        profile = await self.get_profile(profile_id, effective=True)
        client = create_llm_client(config_from_profile(profile))
        return await client.health_check()

    async def list_models(self, provider: str, *, api_base: str | None = None):
        settings = await self.get_settings(effective=True)
        provider_settings = settings.providers.get(provider)
        if provider_settings is None:
            raise ValueError(f"Unknown LLM provider: {provider}")
        client = create_llm_client(
            self._client_config(provider, provider_settings, api_base=api_base)
        )
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
        ai = normalize_ai_settings(doc.get("ai", {}), include_secret=False)
        ai["profiles"] = [profile.model_dump() for profile in profiles]
        ai["default_profile_id"] = default_profile_id
        ai["task_overrides"] = task_overrides
        doc["ai"] = ai
        await self.repo.put_settings_doc(doc)
        invalidate_llm_settings_cache()

    def _normalize_ai(self, raw: dict[str, Any], *, include_secret: bool) -> dict[str, Any]:
        return normalize_ai_settings(raw, include_secret=include_secret)

    def _validate_settings(self, data: dict[str, Any]) -> None:
        validate_ai_settings(data)

    def _client_config(
        self,
        provider: str,
        settings: LLMProviderSettings,
        *,
        api_base: str | None = None,
    ) -> LLMProviderConfig:
        if provider not in PROVIDERS:
            raise ValueError(f"Unknown LLM provider: {provider}")
        resolved_base = (api_base or "").strip() or settings.api_base or PROVIDERS[provider].default_api_base
        api_key = "" if settings.api_key == MASK else str(settings.api_key or "")
        return LLMProviderConfig(
            provider=provider,  # type: ignore[arg-type]
            api_base=resolved_base,
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

    def _privacy_for_provider(self, provider: str) -> str:
        return privacy_for_provider(provider)


def llm_error_payload(exc: Exception) -> dict[str, Any]:
    if isinstance(exc, LLMError):
        return {"code": exc.code, "message": str(exc), "detail": exc.detail}
    message = str(exc)
    if "connection" in message.lower() or "connect" in message.lower():
        message = (
            f"Cannot reach the LLM server ({message}). "
            "For Ollama, ensure it is running and the API base URL is correct."
        )
    return {"code": "LLM_REQUEST_FAILED", "message": message, "detail": ""}


__all__ = [
    "AISettingsService",
    "TASK_DEFAULTS",
    "default_llm_settings",
    "invalidate_llm_settings_cache",
    "llm_error_payload",
]
