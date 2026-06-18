from __future__ import annotations

import base64
import binascii
import io
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_DUTCH_CHARS = re.compile(r"[a-zA-ZàáâãäåæçèéêëìíîïñòóôõöùúûüýÿÀ-ÿ]+")


def extract_text_from_image(image_base64: str) -> tuple[str, dict[str, Any]]:
    """Best-effort OCR for Dutch text from a base64-encoded image."""
    meta: dict[str, Any] = {"engine": None, "warnings": []}

    try:
        raw = _decode_base64_image(image_base64)
    except (binascii.Error, ValueError) as exc:
        return "", {**meta, "error": f"Invalid image data: {exc}"}

    try:
        from PIL import Image  # type: ignore[import-untyped]
    except ImportError:
        meta["warnings"].append("Pillow not installed; OCR unavailable.")
        return "", meta

    try:
        image = Image.open(io.BytesIO(raw))
    except Exception as exc:
        return "", {**meta, "error": f"Could not open image: {exc}"}

    try:
        import pytesseract  # type: ignore[import-untyped]

        text = pytesseract.image_to_string(image, lang="nld+eng")
        meta["engine"] = "pytesseract"
        return _clean_ocr_text(text), meta
    except ImportError:
        meta["warnings"].append(
            "pytesseract not installed. Install tesseract-ocr and pytesseract for photo OCR."
        )
    except Exception as exc:
        logger.warning("OCR failed: %s", exc)
        meta["warnings"].append(f"OCR engine error: {exc}")

    return "", meta


def _decode_base64_image(payload: str) -> bytes:
    data = payload.strip()
    if "," in data and data.lower().startswith("data:"):
        data = data.split(",", 1)[1]
    return base64.b64decode(data, validate=True)


def _clean_ocr_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    cleaned: list[str] = []
    for line in lines:
        if _DUTCH_CHARS.search(line):
            cleaned.append(line)
    return "\n".join(cleaned)


def build_immersion_prompt(extracted_text: str) -> str:
    if not extracted_text.strip():
        return ""
    return (
        "The learner photographed Dutch text in the wild:\n\n"
        f"```\n{extracted_text.strip()}\n```\n\n"
        "Help them understand vocabulary, grammar, and cultural context. "
        "Suggest one short practice exercise."
    )
