from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.app.modules.ai.schemas import LLMSettingsUpdate
from backend.app.modules.ai.service import AISettingsService, invalidate_llm_settings_cache
from backend.app.modules.settings.repository import SettingsRepository
from backend.app.modules.settings.schemas import SettingsDoc

router = APIRouter(prefix="/api/settings", tags=["settings"])

_repo = SettingsRepository()


@router.get("", response_model=SettingsDoc)
async def get_settings():
    return await _repo.get_settings_doc()


@router.put("", response_model=SettingsDoc)
async def put_settings(payload: SettingsDoc):
    service = AISettingsService(_repo)
    try:
        ai_payload = LLMSettingsUpdate.model_validate(payload.ai.model_dump())
        service._validate_settings(ai_payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    saved = await _repo.put_settings_doc(payload.model_dump())
    invalidate_llm_settings_cache()
    return saved
