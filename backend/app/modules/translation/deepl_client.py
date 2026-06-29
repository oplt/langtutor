from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass

import httpx

from backend.app.core.logging import get_log_context

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DeepLTranslationResult:
    text: str
    detected_source_language: str | None = None
    billed_characters: int | None = None
    model_type_used: str | None = None


class DeepLClient:
    def __init__(
        self,
        *,
        auth_key: str,
        api_base_url: str,
        timeout_seconds: float = 10.0,
        model_type: str | None = None,
    ) -> None:
        self.auth_key = auth_key
        self.api_base_url = api_base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.model_type = model_type

    async def translate_text(
        self,
        *,
        text: str,
        source_lang: str = "NL",
        target_lang: str = "EN-US",
        context: str | None = None,
    ) -> DeepLTranslationResult:
        if not text.strip():
            return DeepLTranslationResult(text="")

        payload: dict[str, object] = {
            "text": [text],
            "source_lang": source_lang,
            "target_lang": target_lang,
        }
        if context:
            payload["context"] = context
        if self.model_type:
            payload["model_type"] = self.model_type

        headers = {
            "Authorization": f"DeepL-Auth-Key {self.auth_key}",
            "Content-Type": "application/json",
            "User-Agent": "LanguageApp/1.0",
        }
        url = f"{self.api_base_url}/v2/translate"
        character_count = len(text)
        log_ctx = get_log_context()
        start = time.perf_counter()

        logger.info(
            "deepl_translation_started",
            extra={
                "target_lang": target_lang,
                "source_lang": source_lang,
                "character_count": character_count,
                **log_ctx,
            },
        )

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
            data = response.json()
            translation = data["translations"][0]
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.info(
                "deepl_translation_completed",
                extra={
                    "target_lang": target_lang,
                    "source_lang": source_lang,
                    "character_count": character_count,
                    "duration_ms": duration_ms,
                    "billed_characters": translation.get("billed_characters"),
                    **log_ctx,
                },
            )
            return DeepLTranslationResult(
                text=translation["text"],
                detected_source_language=translation.get("detected_source_language"),
                billed_characters=translation.get("billed_characters"),
                model_type_used=translation.get("model_type_used"),
            )
        except httpx.HTTPStatusError as exc:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.warning(
                "deepl_translation_failed",
                extra={
                    "status_code": exc.response.status_code,
                    "target_lang": target_lang,
                    "source_lang": source_lang,
                    "character_count": character_count,
                    "duration_ms": duration_ms,
                    **log_ctx,
                },
            )
            raise
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.warning(
                "deepl_translation_failed",
                extra={
                    "target_lang": target_lang,
                    "source_lang": source_lang,
                    "character_count": character_count,
                    "duration_ms": duration_ms,
                    **log_ctx,
                },
                exc_info=True,
            )
            raise
