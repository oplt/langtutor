from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from backend.app.bootstrap.routes import register_routes
from backend.app.bootstrap.startup import run_startup_warmup
from backend.app.core.config_validation import validate_runtime_config
from backend.app.core.background import schedule_background
from backend.app.core.config import settings
from backend.app.core.exceptions import AppError
from backend.app.core.health import readiness_report
from backend.app.core.logging import clear_log_context, configure_logging, set_log_context
from backend.app.core.metrics import metrics_registry
from backend.app.core.tracing import setup_tracing
from backend.app.core.rate_limit import InMemoryFixedWindowLimiter, RedisFixedWindowLimiter
from backend.app.core.redis import close_redis, get_redis
from backend.app.db.session import db_healthcheck
from backend.app.modules.ai.service import AISettingsService

configure_logging()
logger = logging.getLogger("backend")
fallback_limiter = InMemoryFixedWindowLimiter()


def _normalize_http_detail(detail: Any) -> Dict[str, Any]:
    if isinstance(detail, dict):
        if "code" in detail and "message" in detail:
            return detail
        return {"code": "http_error", "message": "Request failed.", "details": detail}
    return {"code": "http_error", "message": str(detail)}


def _trace_id_from_headers(request: Request) -> str:
    traceparent = request.headers.get("traceparent", "")
    parts = traceparent.split("-")
    if len(parts) >= 2 and len(parts[1]) == 32:
        return parts[1]
    return uuid.uuid4().hex


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    return getattr(route, "path", request.url.path)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_tracing()
    try:
        await db_healthcheck()
        await validate_runtime_config()
        await AISettingsService().get_settings(effective=True)
        schedule_background(run_startup_warmup(), name="startup_warmup")
        logger.info("Startup: database connectivity OK")
    except AppError as e:
        logger.critical("Startup failed (AppError)", extra={"code": e.code, "details": e.details})
        raise
    except Exception:
        logger.critical("Startup failed (unexpected)", exc_info=True)
        raise

    yield

    await close_redis()


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    cors_origins = settings.cors_origins_list

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        trace_id = _trace_id_from_headers(request)
        request.state.request_id = request_id
        request.state.trace_id = trace_id
        set_log_context(request_id=request_id, trace_id=trace_id)
        start = time.perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            metrics_registry.observe_request(
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                duration_ms=duration_ms,
            )
            logger.exception(
                "http_request_failed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": round(duration_ms, 2),
                    "error_type": exc.__class__.__name__,
                },
            )
            raise
        finally:
            if "response" not in locals():
                clear_log_context()

        duration_ms = (time.perf_counter() - start) * 1000
        route_path = _route_template(request)
        metrics_registry.observe_request(
            method=request.method,
            path=route_path,
            status_code=status_code,
            duration_ms=duration_ms,
        )
        log_extra = {
            "method": request.method,
            "path": route_path,
            "raw_path": request.url.path,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
        }
        if duration_ms >= settings.SLOW_REQUEST_MS:
            logger.warning("http_request_slow", extra=log_extra)
        else:
            logger.info("http_request", extra=log_extra)

        response.headers["x-request-id"] = request_id
        response.headers["x-trace-id"] = trace_id
        clear_log_context()
        return response

    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path
        per_minute: int | None = None
        if path == "/auth/login":
            per_minute = settings.RATE_LIMIT_LOGIN_PER_MIN
        elif path == "/auth/signup":
            per_minute = settings.RATE_LIMIT_SIGNUP_PER_MIN
        elif path in {"/api/learning/quiz/generate", "/api/tutor/message"}:
            per_minute = settings.RATE_LIMIT_ANALYZE_PER_MIN

        if per_minute is not None and per_minute > 0:
            client_ip = request.client.host if request.client else "unknown"
            key = f"{path}:{client_ip}"
            try:
                redis_limiter = RedisFixedWindowLimiter(get_redis())
                allow, retry_after = await redis_limiter.allow(
                    key=key,
                    limit=per_minute,
                    window_seconds=60,
                )
            except Exception:
                allow, retry_after = fallback_limiter.allow(
                    key=key,
                    limit=per_minute,
                    window_seconds=60,
                )
            if not allow:
                rid = getattr(request.state, "request_id", None)
                return JSONResponse(
                    status_code=429,
                    headers={"Retry-After": str(retry_after), "x-request-id": rid or ""},
                    content={
                        "ok": False,
                        "error": {
                            "code": "rate_limited",
                            "message": "Too many requests. Please try again shortly.",
                            "details": {"retry_after_seconds": retry_after},
                        },
                        "request_id": rid,
                    },
                )

        return await call_next(request)

    @app.get("/metrics", include_in_schema=False)
    async def metrics():
        return PlainTextResponse(metrics_registry.render_prometheus(), media_type="text/plain; version=0.0.4")

    @app.get("/health", include_in_schema=False)
    async def health():
        return {"ok": True}

    @app.get("/ready", include_in_schema=False)
    async def ready():
        report = await readiness_report()
        status_code = 200 if report["ok"] else 503
        return JSONResponse(status_code=status_code, content=report)

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        rid = getattr(request.state, "request_id", None)
        logger.warning(
            "AppError",
            extra={"request_id": rid, "code": exc.code, "status_code": exc.status_code, "details": exc.details},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"ok": False, "error": exc.to_dict(), "request_id": rid},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        rid = getattr(request.state, "request_id", None)
        detail = _normalize_http_detail(exc.detail)
        logger.info(
            "HTTPException",
            extra={"request_id": rid, "status_code": exc.status_code, "code": detail.get("code")},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"ok": False, "error": detail, "request_id": rid},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        rid = getattr(request.state, "request_id", None)
        logger.exception("Unhandled exception", extra={"request_id": rid})
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "error": {"code": "internal_error", "message": "Unexpected internal error."},
                "request_id": rid,
            },
        )

    register_routes(app)
    return app


app = create_app()
