from __future__ import annotations

import logging

from backend.app.core.config import settings
from backend.app.modules.translation.cache import get_cached_translation, set_cached_translation
from backend.app.modules.translation.deepl_client import DeepLClient
from backend.app.modules.translation.schemas import TranslationOut

logger = logging.getLogger(__name__)

_TRANSLATION_UNAVAILABLE_WARNING = "English translation is temporarily unavailable."


def _disabled_translation(target_lang: str) -> TranslationOut:
    return TranslationOut(
        provider="deepl",
        language=target_lang,
        status="disabled",
        text=None,
    )


def _unavailable_translation(target_lang: str) -> TranslationOut:
    return TranslationOut(
        provider="deepl",
        language=target_lang,
        status="unavailable",
        text=None,
    )


class TranslationService:
    def __init__(self, deepl_client: DeepLClient | None) -> None:
        self.deepl_client = deepl_client
        self.source_lang = settings.DEEPL_SOURCE_LANG
        self.target_lang = settings.DEEPL_TARGET_LANG
        self.model_type = settings.DEEPL_MODEL_TYPE or None

    @property
    def enabled(self) -> bool:
        return bool(settings.DEEPL_ENABLED and self.deepl_client is not None)

    async def translate_to_english(
        self,
        *,
        text: str,
        context: str | None = None,
        target_lang: str | None = None,
    ) -> tuple[TranslationOut, list[str]]:
        warnings: list[str] = []
        resolved_target = target_lang or self.target_lang

        if not settings.DEEPL_ENABLED:
            return _disabled_translation(resolved_target), warnings

        if self.deepl_client is None:
            warnings.append(_TRANSLATION_UNAVAILABLE_WARNING)
            return _unavailable_translation(resolved_target), warnings

        if not text.strip():
            return TranslationOut(
                provider="deepl",
                language=resolved_target,
                status="ok",
                text="",
            ), warnings

        cached = await get_cached_translation(
            text=text,
            source_lang=self.source_lang,
            target_lang=resolved_target,
            model_type=self.model_type,
        )
        if cached:
            return TranslationOut.model_validate(cached), warnings

        try:
            result = await self.deepl_client.translate_text(
                text=text,
                source_lang=self.source_lang,
                target_lang=resolved_target,
                context=context,
            )
            translation = TranslationOut(
                provider="deepl",
                language=resolved_target,
                status="ok",
                text=result.text,
                detectedSourceLanguage=result.detected_source_language,
                modelTypeUsed=result.model_type_used,
            )
            await set_cached_translation(
                text=text,
                source_lang=self.source_lang,
                target_lang=resolved_target,
                model_type=self.model_type,
                payload=translation.model_dump(mode="json", by_alias=True),
            )
            return translation, warnings
        except Exception:
            logger.warning("translation_unavailable_returning_dutch_only")
            warnings.append(_TRANSLATION_UNAVAILABLE_WARNING)
            return _unavailable_translation(resolved_target), warnings


def build_deepl_client() -> DeepLClient | None:
    if not settings.DEEPL_ENABLED:
        return None
    auth_key = (settings.DEEPL_AUTH_KEY or "").strip()
    if not auth_key:
        logger.warning("deepl_client_disabled_missing_auth_key")
        return None
    return DeepLClient(
        auth_key=auth_key,
        api_base_url=settings.DEEPL_API_BASE_URL,
        timeout_seconds=float(settings.DEEPL_TIMEOUT_SECONDS),
        model_type=settings.DEEPL_MODEL_TYPE or None,
    )


_translation_service: TranslationService | None = None


def get_translation_service() -> TranslationService:
    global _translation_service
    if _translation_service is None:
        _translation_service = TranslationService(build_deepl_client())
    return _translation_service
