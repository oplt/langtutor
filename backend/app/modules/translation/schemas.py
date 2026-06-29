from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TranslationStatus = Literal["ok", "disabled", "unavailable"]


class TranslationOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    provider: str = "deepl"
    language: str = "EN-US"
    status: TranslationStatus
    text: str | None = None
    detected_source_language: str | None = Field(default=None, alias="detectedSourceLanguage")
    model_type_used: str | None = Field(default=None, alias="modelTypeUsed")
