from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.app.modules.users.models import User
from backend.app.modules.auth.dependencies import get_current_user
from backend.app.modules.extensions.sandbox.service import run_sandbox_expression

router = APIRouter(prefix="/api/extensions/sandbox", tags=["extensions-sandbox"])


class SandboxRunIn(BaseModel):
    expression: str = Field(min_length=1, max_length=200)


@router.post("/run")
async def sandbox_run(
    payload: SandboxRunIn,
    user: User = Depends(get_current_user),
):
    _ = user
    return run_sandbox_expression(payload.expression)
