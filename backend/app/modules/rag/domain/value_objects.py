from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AccessContext:
    user_id: str
    organization_id: str | None = None
    project_id: str | None = None
    is_admin: bool = False


@dataclass(frozen=True)
class RetrievalFilters:
    document_ids: list[str] | None = None
    source_types: list[str] | None = None
    extra: dict[str, Any] = field(default_factory=dict)
