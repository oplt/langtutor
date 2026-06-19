"""HTTP error mapping for RAG API routes."""

from __future__ import annotations

import asyncio

import httpx
from fastapi import HTTPException

from backend.app.modules.llm.errors import (
    LLMConfigError,
    LLMError,
    LLMNetworkError,
    LLMProviderUnavailableError,
)


def rag_ask_http_exception(exc: Exception) -> HTTPException:
    """Map RAG ask failures to structured HTTP errors."""
    if isinstance(exc, LLMProviderUnavailableError):
        return HTTPException(
            status_code=503,
            detail={
                "code": exc.code,
                "message": str(exc) or "LLM provider is temporarily unavailable.",
            },
        )
    if isinstance(exc, LLMNetworkError):
        return HTTPException(
            status_code=502,
            detail={
                "code": exc.code,
                "message": str(exc) or "LLM network error while generating the answer.",
            },
        )
    if isinstance(exc, LLMConfigError):
        return HTTPException(
            status_code=500,
            detail={
                "code": exc.code,
                "message": str(exc) or "LLM is misconfigured for RAG answers.",
            },
        )
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError, httpx.TimeoutException)):
        return HTTPException(
            status_code=504,
            detail={
                "code": "RAG_TIMEOUT",
                "message": "RAG answer generation timed out.",
            },
        )
    if isinstance(exc, LLMError):
        return HTTPException(
            status_code=503,
            detail={
                "code": exc.code,
                "message": str(exc) or "LLM request failed.",
            },
        )
    return HTTPException(
        status_code=503,
        detail={
            "code": "RAG_ASK_FAILED",
            "message": "RAG answer generation failed.",
        },
    )
