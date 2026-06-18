from __future__ import annotations

import logging
from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import set_log_context
from backend.app.core.security import TokenError, decode_token
from backend.app.db.session import get_db
from backend.app.modules.users.models import User

logger = logging.getLogger("backend")

bearer = HTTPBearer(auto_error=False)


def auth_error(code: str, message: str, *, details: Optional[dict] = None) -> dict:
    payload = {"code": code, "message": message}
    if details:
        payload["details"] = details
    return payload


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
) -> User:
    if not creds or creds.scheme.lower() != "bearer" or not creds.credentials:
        logger.info("Auth failed: missing bearer token")
        raise HTTPException(status_code=401, detail=auth_error("missing_token", "Missing bearer token."))

    token = creds.credentials.strip()

    try:
        user_id = decode_token(token)
    except TokenError as e:
        logger.info("Auth failed: token decode rejected", extra={"code": e.code, "status_code": e.status_code})
        raise HTTPException(status_code=e.status_code, detail=e.to_dict())

    q = await db.execute(
        select(User)
        .where(User.id == user_id)
        .where(User.is_active.is_(True))
        .where(User.deleted_at.is_(None))
    )
    user = q.scalar_one_or_none()
    if not user:
        logger.info("Auth failed: user not found for token")
        raise HTTPException(status_code=401, detail=auth_error("user_not_found", "User not found."))

    set_log_context(user_id=str(user.id))
    return user
