# backend/utils/security.py
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError, JWTError

from backend.app.core.config import settings
from backend.app.core.exceptions import AppError


ph = PasswordHasher()

JWT_SECRET = settings.JWT_SECRET
JWT_ALG = settings.JWT_ALGORITHM
JWT_EXPIRE_MINUTES = settings.JWT_EXPIRES_MINUTES


# -----------------------------------------------------------------------------
# Typed token errors (subclass AppError so main.py can format them consistently)
# -----------------------------------------------------------------------------

class TokenError(AppError):
    """Base class for token/auth errors (typically 401)."""


class TokenMissingSubject(TokenError):
    def __init__(self):
        super().__init__(
            code="token_missing_sub",
            message="Token missing subject.",
            status_code=401,
        )


class TokenExpired(TokenError):
    def __init__(self):
        super().__init__(
            code="token_expired",
            message="Token has expired.",
            status_code=401,
        )


class TokenInvalid(TokenError):
    def __init__(self, *, reason: str = "invalid"):
        super().__init__(
            code="token_invalid",
            message="Token is invalid.",
            status_code=401,
            details={"reason": reason},
        )


class TokenMalformed(TokenError):
    def __init__(self):
        super().__init__(
            code="token_malformed",
            message="Token is malformed.",
            status_code=401,
        )


# -----------------------------------------------------------------------------
# Password hashing
# -----------------------------------------------------------------------------

def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify password against Argon2 hash.

    Error-handling:
      - Wrong password -> False
      - Corrupt hash / internal errors -> AppError (server issue) to avoid silent auth bugs
    """
    try:
        return ph.verify(hashed_password, password)
    except VerifyMismatchError:
        return False
    except VerificationError as e:
        # Hash corrupted / invalid format / etc.
        raise AppError(
            code="password_hash_invalid",
            message="Password hash verification failed due to invalid hash.",
            status_code=500,
            details={"reason": str(e)},
        )
    except Exception as e:
        raise AppError(
            code="password_verify_failed",
            message="Unexpected failure verifying password.",
            status_code=500,
            details={"reason": str(e)},
        )


def verify_password_and_rehash_if_needed(password: str, hashed_password: str) -> Tuple[bool, Optional[str]]:
    """
    Verify password and indicate whether rehash is needed.

    Returns:
      (ok, new_hash_or_none)
    """
    ok = verify_password(password, hashed_password)
    if not ok:
        return False, None

    try:
        if ph.check_needs_rehash(hashed_password):
            return True, hash_password(password)
    except Exception:
        # Rehash check failing is non-fatal; don't block login
        return True, None

    return True, None


# -----------------------------------------------------------------------------
# JWT helpers
# -----------------------------------------------------------------------------

def create_access_token(user_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=JWT_EXPIRE_MINUTES)

    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def decode_token(token: str) -> uuid.UUID:
    """
    Decode and validate token.

    Raises:
      - TokenExpired / TokenInvalid / TokenMalformed / TokenMissingSubject (401)
      - AppError for unexpected failures (500)
    """
    if not token or not isinstance(token, str):
        raise TokenMalformed()

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except ExpiredSignatureError:
        raise TokenExpired()
    except JWTClaimsError:
        # Claims issues (bad exp/iat/nbf, etc.)
        raise TokenInvalid(reason="invalid_claims")
    except JWTError:
        # Signature invalid, token tampered, etc.
        raise TokenInvalid(reason="invalid_token")
    except Exception as e:
        raise AppError(
            code="token_decode_failed",
            message="Unexpected failure decoding token.",
            status_code=500,
            details={"reason": str(e)},
        )

    sub = payload.get("sub")
    if sub is None:
        raise TokenMissingSubject()

    try:
        return sub if isinstance(sub, uuid.UUID) else uuid.UUID(str(sub))
    except Exception:
        raise TokenInvalid(reason="sub_not_uuid")


def try_decode_token(token: str) -> Optional[uuid.UUID]:
    """
    Backward-compatible helper:
      - Returns UUID if valid, else None.
      - Useful if you still want old-style behavior in some places.
    """
    try:
        return decode_token(token)
    except TokenError:
        return None


def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify token and return full payload if valid.

    Raises typed token errors instead of returning None.
    """
    if not token or not isinstance(token, str):
        raise TokenMalformed()
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except ExpiredSignatureError:
        raise TokenExpired()
    except JWTError:
        raise TokenInvalid(reason="invalid_token")
    except Exception as e:
        raise AppError(
            code="token_verify_failed",
            message="Unexpected failure verifying token.",
            status_code=500,
            details={"reason": str(e)},
        )
