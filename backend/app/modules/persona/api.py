from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.app.modules.persona.schemas import PersonaDetailOut, PersonaOut
from backend.app.modules.persona.service import PersonaNotFoundError, get_persona, list_personas

router = APIRouter(prefix="/api/personas", tags=["personas"])


@router.get("")
async def list_all_personas():
    personas = list_personas()
    return {"personas": [PersonaOut(**persona.to_dict()) for persona in personas]}


@router.get("/{name}")
async def get_persona_detail(name: str):
    try:
        persona = get_persona(name)
    except PersonaNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PersonaDetailOut(**persona.to_dict())
