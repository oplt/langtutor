from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.modules.auth.dependencies import get_current_user
from backend.app.modules.prompt.assembler import build_system_prompt
from backend.app.modules.prompt.manager import AVAILABLE_PACKS, get_prompt_manager
from backend.app.modules.users.models import User

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


@router.get("/packs")
async def list_prompt_packs(_user: User = Depends(get_current_user)) -> dict:
    manager = get_prompt_manager()
    return {
        "packs": list(AVAILABLE_PACKS),
        "on_disk": manager.list_packs(),
        "languages": ["en", "nl"],
    }


@router.get("/packs/{pack}")
async def get_prompt_pack(
    pack: str,
    language: str = Query(default="en"),
    cefr_level: str | None = Query(default=None),
    _user: User = Depends(get_current_user),
) -> dict:
    if pack not in AVAILABLE_PACKS:
        raise HTTPException(status_code=404, detail=f"Unknown pack: {pack}")
    manager = get_prompt_manager()
    raw = manager.load_pack(pack, language)
    assembled = build_system_prompt(
        pack=pack,
        ui_language=language,
        cefr_level=cefr_level,
    )
    return {
        "pack": pack,
        "language": language,
        "cefr_level": cefr_level,
        "raw": raw,
        "assembled_system_prompt": assembled,
    }
