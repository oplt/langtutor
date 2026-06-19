# backend/db/session.py
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from backend.app.core.config import settings
from backend.app.core.exceptions import AppError
from backend.app.core.logging import configure_logging
import backend.app.db.model_registry  # noqa: F401 -- load model classes for SQLAlchemy relationships

configure_logging()
logger = logging.getLogger(__name__)


def is_expected_client_error(exc: BaseException) -> bool:
    """HTTP/validation/app errors that should rollback quietly without error tracebacks."""
    return isinstance(exc, (HTTPException, RequestValidationError, AppError))


def build_engine() -> AsyncEngine:
    """
    Build a SQLAlchemy AsyncEngine with sane production defaults.

    Raises:
      AppError: when DATABASE_URL is missing/misconfigured in a way that prevents engine creation.
    """
    db_url = getattr(settings, "DATABASE_URL", None)
    if not db_url or not isinstance(db_url, str):
        raise AppError(
            code="db_config_missing",
            message="DATABASE_URL is not configured.",
            status_code=500,
        )

    try:
        return create_async_engine(
            db_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            future=True,
        )
    except Exception as e:
        # Engine creation failing is a server configuration issue
        logger.exception("Database engine initialization failed")
        raise AppError(
            code="db_engine_init_failed",
            message="Failed to initialize database engine.",
            status_code=500,
            details={"reason": str(e)},
        )


engine: AsyncEngine = build_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """
    Context manager for transactional session usage (non-FastAPI contexts).

    Commits on success, rollbacks on exception.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as exc:
            await session.rollback()
            if is_expected_client_error(exc):
                logger.debug(
                    "Session rollback in session_scope",
                    extra={"reason": exc.__class__.__name__},
                )
            else:
                logger.warning("Session rollback in session_scope", exc_info=True)
            raise


async def get_db() -> AsyncIterator[AsyncSession]:
    """
    FastAPI dependency that provides an AsyncSession.

    Behavior:
      - commit if request succeeds
      - rollback if any exception occurs
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as exc:
            await session.rollback()
            if is_expected_client_error(exc):
                logger.debug(
                    "Session rollback in get_db",
                    extra={"reason": exc.__class__.__name__},
                )
            else:
                logger.warning("Session rollback in get_db", exc_info=True)
            raise


async def db_healthcheck() -> None:
    """
    Optional healthcheck helper.
    Call this at startup or from a /health endpoint to verify DB connectivity.

    Raises:
      AppError: if DB is unreachable.
    """
    try:
        async with engine.connect() as conn:
            # Wrap raw SQL string in text() function
            await conn.execute(text("SELECT 1"))
            logger.info("Database health check passed")
    except SQLAlchemyError as e:
        logger.error("Database health check failed", extra={"reason": str(e)})
        raise AppError(
            code="db_unreachable",
            message="Database is unreachable.",
            status_code=503,
            details={"reason": str(e)},
        )
