from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any


class SkillPlaybookOut(BaseModel):
    level: str
    title: str
    version: str
    updated_at: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class SkillPlaybookContentOut(BaseModel):
    level: str
    title: str
    version: str
    content: str
