from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.app.modules.users.models import User
from backend.app.modules.auth.dependencies import get_current_user
from backend.app.modules.extensions.vision.service import (
    build_immersion_prompt,
    extract_text_from_image,
)

router = APIRouter(prefix="/api/extensions/vision", tags=["extensions-vision"])


class VisionOcrIn(BaseModel):
    image_base64: str | None = None
    text: str | None = Field(default=None, max_length=8000)


class VisionOcrOut(BaseModel):
    text: str
    meta: dict
    tutor_prompt: str = ""


@router.post("/ocr", response_model=VisionOcrOut)
async def vision_ocr(
    payload: VisionOcrIn,
    user: User = Depends(get_current_user),
):
    _ = user
    meta: dict = {}
    text = (payload.text or "").strip()

    if not text and payload.image_base64:
        text, meta = extract_text_from_image(payload.image_base64)

    if not text:
        meta.setdefault(
            "hint",
            "Provide `text` directly or install Pillow + pytesseract for image OCR.",
        )

    return VisionOcrOut(
        text=text,
        meta=meta,
        tutor_prompt=build_immersion_prompt(text),
    )
