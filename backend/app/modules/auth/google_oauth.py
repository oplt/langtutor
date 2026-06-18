from __future__ import annotations

import logging
from typing import Optional
from urllib import parse as urllib_parse

import httpx
from fastapi.responses import RedirectResponse

from backend.app.core.config import settings

logger = logging.getLogger("backend")


def google_callback_redirect(
    path: str = "/",
    token: Optional[str] = None,
    error: Optional[str] = None,
) -> RedirectResponse:
    base = settings.FRONTEND_BASE_URL.rstrip("/")
    page = "/" if path in {"/", "/signin", "/signup"} else path
    fragment = ""
    if token:
        fragment = f"#access_token={urllib_parse.quote(token, safe='')}&provider=google"
    elif error:
        fragment = f"#error={urllib_parse.quote(error, safe='')}"
    return RedirectResponse(url=f"{base}{page}{fragment}", status_code=302)


async def google_exchange_code(code: str) -> Optional[dict]:
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            return response.json()
    except (httpx.HTTPError, ValueError):
        logger.warning("Google OAuth code exchange failed", exc_info=True)
        return None


async def google_verify_id_token(id_token: str) -> Optional[dict]:
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": id_token},
            )
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError):
        logger.warning("Google OAuth token verification failed", exc_info=True)
        return None

    aud = payload.get("aud")
    email = payload.get("email")
    email_verified = str(payload.get("email_verified", "")).lower() in {"true", "1"}
    if aud != settings.GOOGLE_CLIENT_ID or not email or not email_verified:
        return None
    return payload
