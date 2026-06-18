from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from backend.app.modules.settings.defaults import build_default_settings_doc
from backend.app.modules.settings.schemas import SettingsDoc
from backend.app.core.config import BASE_DIR

logger = logging.getLogger(__name__)

MASK = "********"
SETTINGS_PATH = BASE_DIR / "data" / "runtime" / "settings.json"
SECRETS_PATH = BASE_DIR / "data" / "runtime" / "settings.secrets.json"


class SettingsRepository:
    def __init__(self, settings_path: Path | None = None, secrets_path: Path | None = None) -> None:
        self.settings_path = settings_path or SETTINGS_PATH
        self.secrets_path = secrets_path or SECRETS_PATH

    async def get_settings_doc(self) -> SettingsDoc:
        doc = await asyncio.to_thread(self._load_doc)
        return SettingsDoc.model_validate(self._mask_secrets(doc))

    async def get_effective_settings_doc(self) -> dict[str, Any]:
        doc = await asyncio.to_thread(self._load_doc)
        return self._merge_secrets(doc)

    async def put_settings_doc(self, payload: dict[str, Any]) -> SettingsDoc:
        current = self._merge_secrets(await asyncio.to_thread(self._load_doc))
        merged = deepcopy(current)
        merged.update(payload)
        merged["updated_at"] = datetime.now(UTC).isoformat()
        await asyncio.to_thread(self._persist, merged)
        return await self.get_settings_doc()

    def _load_doc(self) -> dict[str, Any]:
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.settings_path.exists():
            default_doc = build_default_settings_doc()
            self._persist(default_doc)
            return default_doc
        try:
            raw = json.loads(self.settings_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("Corrupt settings file; resetting to defaults.")
            default_doc = build_default_settings_doc()
            self._persist(default_doc)
            return default_doc
        if not isinstance(raw, dict):
            return build_default_settings_doc()
        return raw

    def _persist(self, doc: dict[str, Any]) -> None:
        public = self._mask_secrets(doc)
        secrets = self._extract_secrets(doc)
        self._atomic_write_json(self.settings_path, public)
        self._atomic_write_json(self.secrets_path, secrets)

    def _atomic_write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, path)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

    def _merge_secrets(self, doc: dict[str, Any]) -> dict[str, Any]:
        merged = deepcopy(doc)
        if not self.secrets_path.exists():
            return merged
        try:
            secrets = json.loads(self.secrets_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return merged
        if not isinstance(secrets, dict):
            return merged
        ai = merged.setdefault("ai", {})
        for provider_id, api_key in (secrets.get("provider_keys") or {}).items():
            providers = ai.setdefault("providers", {})
            entry = providers.setdefault(provider_id, {})
            if api_key:
                entry["api_key"] = api_key
                entry["has_api_key"] = True
        for profile_id, api_key in (secrets.get("profile_keys") or {}).items():
            for profile in ai.get("profiles") or []:
                if isinstance(profile, dict) and profile.get("id") == profile_id and api_key:
                    profile["api_key"] = api_key
                    profile["has_api_key"] = True
        legacy = secrets.get("llm_api_key")
        if legacy:
            ai["llm_api_key"] = legacy
        return merged

    def _mask_secrets(self, doc: dict[str, Any]) -> dict[str, Any]:
        masked = deepcopy(doc)
        ai = masked.get("ai")
        if not isinstance(ai, dict):
            return masked
        for provider in (ai.get("providers") or {}).values():
            if isinstance(provider, dict) and provider.get("api_key"):
                provider["api_key"] = None
        for profile in ai.get("profiles") or []:
            if isinstance(profile, dict) and profile.get("has_api_key"):
                profile["api_key"] = None
        if ai.get("llm_api_key"):
            ai["llm_api_key"] = None
        return masked

    def _extract_secrets(self, doc: dict[str, Any]) -> dict[str, Any]:
        ai = doc.get("ai") or {}
        provider_keys: dict[str, str] = {}
        for provider_id, provider in (ai.get("providers") or {}).items():
            if not isinstance(provider, dict):
                continue
            api_key = provider.get("api_key")
            if api_key and api_key != MASK:
                provider_keys[str(provider_id)] = str(api_key)
        profile_keys: dict[str, str] = {}
        for profile in ai.get("profiles") or []:
            if not isinstance(profile, dict):
                continue
            api_key = profile.get("api_key")
            if api_key and api_key != MASK:
                profile_keys[str(profile.get("id") or "")] = str(api_key)
        secrets: dict[str, Any] = {"provider_keys": provider_keys, "profile_keys": profile_keys}
        legacy = ai.get("llm_api_key")
        if legacy and legacy != MASK:
            secrets["llm_api_key"] = legacy
        return secrets
