from __future__ import annotations

from fastapi import Depends, HTTPException

from backend.app.core.config import settings
from backend.app.modules.auth.dependencies import auth_error, get_current_user
from backend.app.modules.users.models import User


async def require_knowledge_admin(
    user: User = Depends(get_current_user),
) -> User:
    allowed = settings.knowledge_admin_emails_list
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail=auth_error(
                "knowledge_admin_unconfigured",
                "Knowledge base administration is not configured.",
            ),
        )
    if user.email.strip().lower() not in allowed:
        raise HTTPException(
            status_code=403,
            detail=auth_error(
                "knowledge_admin_forbidden",
                "You are not authorized to manage knowledge bases.",
            ),
        )
    return user
