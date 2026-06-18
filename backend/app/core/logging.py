from __future__ import annotations

import contextvars
import json
import logging
from logging.handlers import WatchedFileHandler
from pathlib import Path
from typing import Any

from backend.app.core.config import BASE_DIR, settings


_RESERVED_RECORD_KEYS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "message",
    "asctime",
}

_request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)
_trace_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("trace_id", default=None)
_user_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("user_id", default=None)
_UNSET = object()


def set_log_context(
    *,
    request_id: str | None | object = _UNSET,
    trace_id: str | None | object = _UNSET,
    user_id: str | None | object = _UNSET,
) -> None:
    if request_id is not _UNSET:
        _request_id_var.set(request_id if isinstance(request_id, str) else None)
    if trace_id is not _UNSET:
        _trace_id_var.set(trace_id if isinstance(trace_id, str) else None)
    if user_id is not _UNSET:
        _user_id_var.set(user_id if isinstance(user_id, str) else None)


def clear_log_context() -> None:
    set_log_context(request_id=None, trace_id=None, user_id=None)


def get_log_context() -> dict[str, str | None]:
    return {
        "request_id": _request_id_var.get(),
        "trace_id": _trace_id_var.get(),
        "user_id": _user_id_var.get(),
    }


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = _request_id_var.get()
        if not hasattr(record, "trace_id"):
            record.trace_id = _trace_id_var.get()
        if not hasattr(record, "user_id"):
            record.user_id = _user_id_var.get()
        return True


class KeyValueFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        timestamp = self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S")
        message = record.getMessage()
        extras: list[str] = []
        for key, value in sorted(record.__dict__.items()):
            if key in _RESERVED_RECORD_KEYS or key.startswith("_"):
                continue
            extras.append(f"{key}={value!r}")

        base = f"{timestamp} level={record.levelname} logger={record.name} message={message!r}"
        if extras:
            base = f"{base} {' '.join(extras)}"

        if record.exc_info:
            return f"{base}\n{self.formatException(record.exc_info)}"
        return base


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in sorted(record.__dict__.items()):
            if key in _RESERVED_RECORD_KEYS or key.startswith("_"):
                continue
            if value is not None:
                payload[key] = _json_safe(value)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


def _resolve_log_path(raw_path: str) -> Path:
    candidate = Path(raw_path.strip() or "logs/app.log")
    if candidate.is_absolute():
        return candidate
    return BASE_DIR / candidate


def _coerce_level(level_raw: Any) -> int:
    level_name = str(level_raw or "INFO").strip().upper()
    return getattr(logging, level_name, logging.INFO)


def configure_logging() -> Path:
    if getattr(configure_logging, "_configured", False):
        return getattr(configure_logging, "_log_path")

    root_logger = logging.getLogger()
    level = _coerce_level(getattr(settings, "LOG_LEVEL", "INFO"))
    root_logger.setLevel(level)
    for handler in list(root_logger.handlers):
        if getattr(handler, "_languageapp_handler", False):
            root_logger.removeHandler(handler)
    context_filter = ContextFilter()
    root_logger.addFilter(context_filter)

    log_path = _resolve_log_path(getattr(settings, "LOG_FILE_PATH", "logs/app.log"))
    log_path.parent.mkdir(parents=True, exist_ok=True)
    formatter: logging.Formatter
    if bool(getattr(settings, "LOG_JSON", True)):
        formatter = JsonFormatter()
    else:
        formatter = KeyValueFormatter()

    file_handler = WatchedFileHandler(log_path, encoding="utf-8")
    file_handler._languageapp_handler = True  # type: ignore[attr-defined]
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(context_filter)
    root_logger.addHandler(file_handler)

    if bool(getattr(settings, "LOG_TO_STDOUT", True)):
        stream_handler = logging.StreamHandler()
        stream_handler._languageapp_handler = True  # type: ignore[attr-defined]
        stream_handler.setLevel(level)
        stream_handler.setFormatter(formatter)
        stream_handler.addFilter(context_filter)
        root_logger.addHandler(stream_handler)

    for noisy_logger in ("uvicorn.access", "httpx"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)

    configure_logging._configured = True
    configure_logging._log_path = log_path

    root_logger.info(
        "Logging configured",
        extra={"log_file": str(log_path), "log_level": logging.getLevelName(level)},
    )
    return log_path
