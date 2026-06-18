from __future__ import annotations

import logging

from fastapi import WebSocket
from sqlalchemy import select

from backend.app.core.security import TokenError, decode_token
from backend.app.db.session import AsyncSessionLocal
from backend.app.modules.auth.ws_tokens import extract_ws_token
from backend.app.modules.users.models import User

logger = logging.getLogger("backend")

WS_AUTH_FAILED = object()


async def ws_require_user(ws: WebSocket) -> User | object:
    token = extract_ws_token(ws)
    if not token:
        await ws.close(code=4401, reason="Missing token")
        return WS_AUTH_FAILED

    try:
        user_id = decode_token(token)
    except TokenError:
        await ws.close(code=4401, reason="Invalid token")
        return WS_AUTH_FAILED

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User)
            .where(User.id == user_id)
            .where(User.is_active.is_(True))
            .where(User.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()

    if user is None:
        await ws.close(code=4401, reason="User not found")
        return WS_AUTH_FAILED

    return user
