from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import yaml

PACKS_ROOT = Path(__file__).resolve().parent / "packs"

logger = logging.getLogger(__name__)

# UI / prompt locale → fallback chain
LANGUAGE_FALLBACKS: dict[str, list[str]] = {
    "en": ["en", "nl"],
    "nl": ["nl", "en"],
}

# LLM task names → on-disk prompt pack id
TASK_TO_PACK: dict[str, str] = {
    "chat": "conversation",
    "tutor_chat": "conversation",
    "correction": "correction",
    "story_generation": "story",
    "quiz_generation": "quiz",
    "grammar_explanation": "conversation",
    "placement": "conversation",
}

AVAILABLE_PACKS = ("conversation", "correction", "story", "quiz")


def normalize_language(language: str | None) -> str:
    raw = (language or "en").strip().lower()
    if raw.startswith("nl"):
        return "nl"
    return "en"


class PromptManager:
    """Load cached YAML prompt packs with language fallback."""

    _instance: PromptManager | None = None

    def __new__(cls) -> PromptManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._cache = {}
        return cls._instance

    def __init__(self) -> None:
        if not hasattr(self, "_cache"):
            self._cache: dict[str, dict[str, Any]] = {}

    def load_pack(self, pack: str, language: str = "en") -> dict[str, Any]:
        lang = normalize_language(language)
        cache_key = f"{pack}_{lang}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        loaded = self._load_with_fallback(pack, lang)
        self._cache[cache_key] = loaded
        return loaded

    def load_task(self, task: str, language: str = "en") -> dict[str, Any]:
        pack = TASK_TO_PACK.get(task, task)
        return self.load_pack(pack, language)

    def get_text(
        self,
        prompts: dict[str, Any],
        *path: str,
        fallback: str = "",
    ) -> str:
        value: Any = prompts
        for key in path:
            if not isinstance(value, dict) or key not in value:
                return fallback
            value = value[key]
        return value if isinstance(value, str) else fallback

    def clear_cache(self, pack: str | None = None) -> None:
        if pack is None:
            self._cache.clear()
            return
        prefix = f"{pack}_"
        for key in list(self._cache):
            if key.startswith(prefix):
                del self._cache[key]

    def reload_pack(self, pack: str, language: str = "en") -> dict[str, Any]:
        lang = normalize_language(language)
        cache_key = f"{pack}_{lang}"
        self._cache.pop(cache_key, None)
        return self.load_pack(pack, language)

    def list_packs(self) -> list[str]:
        if not PACKS_ROOT.exists():
            return []
        packs: set[str] = set()
        for lang_dir in PACKS_ROOT.iterdir():
            if not lang_dir.is_dir():
                continue
            for path in lang_dir.glob("*.yaml"):
                packs.add(path.stem)
        return sorted(packs)

    def _load_with_fallback(self, pack: str, lang: str) -> dict[str, Any]:
        chain = LANGUAGE_FALLBACKS.get(lang, ["en", "nl"])
        for candidate in chain:
            path = PACKS_ROOT / candidate / f"{pack}.yaml"
            if not path.exists():
                continue
            try:
                with path.open(encoding="utf-8") as handle:
                    data = yaml.safe_load(handle) or {}
                if isinstance(data, dict):
                    return data
            except Exception:
                logger.warning("prompt_pack_load_failed pack=%s lang=%s path=%s", pack, candidate, path, exc_info=True)
                continue
        return {}


_manager: PromptManager | None = None


def get_prompt_manager() -> PromptManager:
    global _manager
    if _manager is None:
        _manager = PromptManager()
    return _manager
