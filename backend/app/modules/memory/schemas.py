from __future__ import annotations

from pydantic import BaseModel, Field


class MemoryPreferenceIn(BaseModel):
    text: str = Field(min_length=1, max_length=240)
    op: str = Field(default="add", pattern="^(add|edit)$")
    target_id: str = ""


class MemoryL2FactIn(BaseModel):
    surface: str = "tutor"
    text: str = Field(min_length=1, max_length=240)


class MemoryDocOut(BaseModel):
    key: str
    content: str
    entries: list[dict]
