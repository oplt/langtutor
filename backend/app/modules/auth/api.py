from __future__ import annotations

import logging
import hashlib
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from backend.app.db.session import get_db
from backend.app.modules.auth.dependencies import auth_error, get_current_user
from backend.app.modules.auth.schemas import (
    AuthOut,
    LoginIn,
    SignUpIn,
    UserOut,
    UserProfileUpdateIn,
)
from backend.app.modules.users.models import User
from backend.app.modules.auth.google_oauth import (
    google_callback_redirect,
    google_exchange_code,
    google_verify_id_token,
)
from backend.app.modules.auth.oauth_state import (
    google_oauth_state_put,
    google_oauth_state_take,
)

logger = logging.getLogger("backend")

router = APIRouter(prefix="/auth", tags=["auth"])


def _email_hash(email: str) -> str:
    return hashlib.sha256(email.encode("utf-8")).hexdigest()[:12]


@router.post("/signup", response_model=AuthOut)
async def signup(payload: SignUpIn, db: AsyncSession = Depends(get_db)):
    email = payload.email.lower().strip()

    if len(payload.password.encode("utf-8")) > 60:
        raise HTTPException(
            status_code=400,
            detail=auth_error("password_too_long", "Password too long (max 60 bytes)."),
        )

    q = await db.execute(
        select(User)
        .where(User.email == email)
        .where(User.is_active.is_(True))
        .where(User.deleted_at.is_(None))
    )
    if q.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=auth_error("email_taken", "Email already registered."))

    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        gender=payload.gender,
        age=payload.age,
        native_language=payload.native_language,
        target_language=payload.target_language,
        cefr_goal=payload.cefr_goal,
    )

    db.add(user)
    try:
        await db.flush()
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        logger.info("Signup integrity error", extra={"email_hash": _email_hash(email)})
        raise HTTPException(status_code=409, detail=auth_error("email_taken", "Email already registered.")) from e
    except SQLAlchemyError as e:
        await db.rollback()
        logger.exception("Signup DB error", extra={"email_hash": _email_hash(email)})
        raise HTTPException(status_code=500, detail=auth_error("db_error", "Database error during signup.")) from e
    except Exception as e:
        await db.rollback()
        logger.exception("Signup unexpected error", extra={"email_hash": _email_hash(email)})
        raise HTTPException(status_code=500, detail=auth_error("internal_error", "Unexpected internal error.")) from e

    token = create_access_token(user.id)
    logger.info("Signup success", extra={"user_id": str(user.id), "email_hash": _email_hash(email)})
    return {"access_token": token, "user": user}


@router.post("/login", response_model=AuthOut)
async def login(payload: LoginIn, db: AsyncSession = Depends(get_db)):
    email = payload.email.lower().strip()

    try:
        q = await db.execute(
            select(User)
            .where(User.email == email)
            .where(User.is_active.is_(True))
            .where(User.deleted_at.is_(None))
        )
        user = q.scalar_one_or_none()
    except SQLAlchemyError as e:
        logger.exception("Login DB error", extra={"email_hash": _email_hash(email)})
        raise HTTPException(status_code=500, detail=auth_error("db_error", "Database error during login.")) from e

    if not user or not verify_password(payload.password, user.hashed_password):
        logger.info("Login failed: invalid credentials", extra={"email_hash": _email_hash(email)})
        raise HTTPException(status_code=401, detail=auth_error("invalid_credentials", "Invalid credentials."))

    token = create_access_token(user.id)
    logger.info("Login success", extra={"user_id": str(user.id), "email_hash": _email_hash(email)})
    return {"access_token": token, "user": user}


@router.get("/google/login")
async def google_login(
    mode: str = Query(default="signin", pattern="^(signin|signup)$"),
):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=503,
            detail=auth_error("google_oauth_not_configured", "Google OAuth is not configured on server."),
        )

    state = await google_oauth_state_put(mode)
    params = urllib_parse.urlencode(
        {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "prompt": "select_account",
            "access_type": "online",
        }
    )
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{params}"
    return RedirectResponse(url=url, status_code=302)


@router.get("/google/callback")
async def google_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    if error:
        logger.warning("Google callback denied by provider", extra={"error": error})
        return google_callback_redirect(error="google_authorization_denied")
    if not code or not state:
        logger.warning("Google callback missing required parameters")
        return google_callback_redirect(error="google_missing_callback_data")

    mode = await google_oauth_state_take(state)
    if not mode:
        logger.warning("Google callback invalid state", extra={"state_present": bool(state)})
        return google_callback_redirect(error="google_invalid_state")

    token_payload = await google_exchange_code(code)
    if not token_payload:
        logger.warning("Google callback code exchange failed")
        return google_callback_redirect(error="google_code_exchange_failed")

    id_token = token_payload.get("id_token")
    if not isinstance(id_token, str) or not id_token:
        logger.warning("Google callback missing id_token")
        return google_callback_redirect(error="google_missing_id_token")

    verified = await google_verify_id_token(id_token)
    if not verified:
        logger.warning("Google callback token verification failed")
        return google_callback_redirect(error="google_invalid_token")

    email = str(verified.get("email", "")).lower().strip()
    full_name = str(verified.get("name", "")).strip() or None
    if not email:
        logger.warning("Google callback missing email claim")
        return google_callback_redirect(error="google_missing_email")

    q = await db.execute(
        select(User)
        .where(User.email == email)
        .where(User.is_active.is_(True))
        .where(User.deleted_at.is_(None))
    )
    user = q.scalar_one_or_none()

    if not user:
        user = User(
            email=email,
            hashed_password=hash_password(secrets.token_urlsafe(24)),
            full_name=full_name,
        )
        db.add(user)
        try:
            await db.flush()
            await db.commit()
        except IntegrityError:
            await db.rollback()
            q2 = await db.execute(
                select(User)
                .where(User.email == email)
                .where(User.is_active.is_(True))
                .where(User.deleted_at.is_(None))
            )
            user = q2.scalar_one_or_none()
            if not user:
                logger.exception("Google callback user creation race failed")
                return google_callback_redirect(error="google_user_create_failed")
        except Exception:
            await db.rollback()
            logger.exception("Google callback user creation failed")
            return google_callback_redirect(error="google_user_create_failed")

    token = create_access_token(user.id)
    logger.info("Google auth success", extra={"user_id": str(user.id), "mode": mode})
    return google_callback_redirect(token=token)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserOut)
async def update_me(
    payload: UserProfileUpdateIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    updates = payload.model_dump(exclude_unset=True)

    def _normalize_text(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned if cleaned else None

    for field in ("full_name", "gender", "native_language", "target_language", "cefr_goal"):
        if field in updates:
            setattr(user, field, _normalize_text(updates[field]))
    if "age" in updates:
        user.age = updates["age"]

    await db.flush()
    await db.commit()
    await db.refresh(user)
    return user
