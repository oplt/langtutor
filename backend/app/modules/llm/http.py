from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import urlparse

import httpx

from backend.app.core.config import settings

logger = logging.getLogger(__name__)


def _safe_target(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.hostname or "unknown"
    port = parsed.port
    if port:
        return f"{host}:{port}"
    return host


async def request_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    timeout_seconds: float = 60.0,
) -> tuple[int, dict[str, Any] | list[Any] | str]:
    req_headers = dict(headers or {})
    timeout = httpx.Timeout(timeout_seconds)
    start = time.perf_counter()
    target = _safe_target(url)
    logger.debug(
        "external_request_started",
        extra={"method": method.upper(), "target": target},
    )
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            request_kwargs: dict[str, Any] = {
                "method": method.upper(),
                "url": url,
                "headers": req_headers,
            }
            if body is not None:
                request_kwargs["json"] = body
            response = await client.request(**request_kwargs)
            status = response.status_code
            raw = response.text
            if not raw:
                payload: dict[str, Any] | list[Any] | str = {}
            else:
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    payload = raw
    except httpx.ConnectError as exc:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.warning(
            "external_request_unreachable",
            extra={
                "method": method.upper(),
                "target": target,
                "duration_ms": duration_ms,
                "error_type": exc.__class__.__name__,
                "error": str(exc),
            },
        )
        raise
    except Exception:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.exception(
            "external_request_failed",
            extra={"method": method.upper(), "target": target, "duration_ms": duration_ms},
        )
        raise
    else:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        extra = {
            "method": method.upper(),
            "target": target,
            "status_code": status,
            "duration_ms": duration_ms,
        }
        if duration_ms >= settings.SLOW_EXTERNAL_CALL_MS:
            logger.warning("external_request_slow", extra=extra)
        elif status >= 400:
            logger.warning("external_request_error_status", extra=extra)
        else:
            logger.info("external_request_complete", extra=extra)
        return status, payload


async def stream_post_lines(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    timeout_seconds: float = 60.0,
) -> AsyncIterator[str]:
    req_headers = dict(headers or {})
    req_headers.setdefault("Content-Type", "application/json")
    timeout = httpx.Timeout(
        connect=min(30.0, timeout_seconds),
        read=None,
        write=timeout_seconds,
        pool=timeout_seconds,
    )
    target = _safe_target(url)
    start = time.perf_counter()
    logger.debug("external_stream_started", extra={"target": target})
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream(
            "POST",
            url,
            headers=req_headers,
            json=body or {},
        ) as response:
            if response.status_code >= 400:
                detail = (await response.aread()).decode("utf-8", errors="replace")
                duration_ms = round((time.perf_counter() - start) * 1000, 2)
                logger.error(
                    "external_stream_failed",
                    extra={
                        "target": target,
                        "status_code": response.status_code,
                        "duration_ms": duration_ms,
                    },
                )
                raise RuntimeError(f"HTTP {response.status_code}: {detail}")
            async for line in response.aiter_lines():
                if line:
                    yield line.rstrip("\r\n")
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    extra = {"target": target, "duration_ms": duration_ms}
    if duration_ms >= settings.SLOW_EXTERNAL_CALL_MS:
        logger.warning("external_stream_slow", extra=extra)
    else:
        logger.info("external_stream_complete", extra=extra)
