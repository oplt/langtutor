from __future__ import annotations

from pydantic import BaseModel


class PersonaOut(BaseModel):
    name: str
    description: str
    source: str = "builtin"


class PersonaDetailOut(BaseModel):
    name: str
    description: str
    content: str
    source: str = "builtin"
