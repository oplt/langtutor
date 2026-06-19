from __future__ import annotations

import contextvars
import json
import logging
import re
import time
from contextlib import contextmanager
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlsplit, urlunsplit

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

_SENSITIVE_KEY_RE = re.compile(
    r"(password|passwd|secret|token|api[_-]?key|authorization|auth_header|cookie|jwt|bearer)",
    re.IGNORECASE,
)
_URL_CREDENTIALS_RE = re.compile(r"://([^:@/]+:)([^@/]+)@")
_REDACTED = "***REDACTED***"

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


def get_request_id() -> str | None:
    return _request_id_var.get()


def redact_sensitive_value(key: str, value: Any) -> Any:
    if value is None:
        return value
    key_text = str(key)
    if _SENSITIVE_KEY_RE.search(key_text):
        return _REDACTED
    if isinstance(value, str):
        if _SENSITIVE_KEY_RE.search(value):
            return _REDACTED
        if "://" in value and "@" in value:
            return _URL_CREDENTIALS_RE.sub(r"://\1***@", value)
    if isinstance(value, dict):
        return {k: redact_sensitive_value(str(k), v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact_sensitive_value(key_text, item) for item in value]
    return value


def redact_url(url: str) -> str:
    parts = urlsplit(url)
    if not parts.password and "@" not in parts.netloc:
        return url
    username = parts.username or ""
    host = parts.hostname or ""
    if parts.port:
        host = f"{host}:{parts.port}"
    if username:
        netloc = f"{username}:***@{host}"
    else:
        netloc = f":***@{host}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = _request_id_var.get()
        if not hasattr(record, "trace_id"):
            record.trace_id = _trace_id_var.get()
        if not hasattr(record, "user_id"):
            record.user_id = _user_id_var.get()
        return True


class SensitiveDataFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = str(redact_sensitive_value("message", record.msg))
        for key, value in list(record.__dict__.items()):
            if key in _RESERVED_RECORD_KEYS or key.startswith("_"):
                continue
            setattr(record, key, redact_sensitive_value(key, value))
        return True


class KeyValueFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        timestamp = self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S")
        message = record.getMessage()
        extras: list[str] = []
        for key, value in sorted(record.__dict__.items()):
            if key in _RESERVED_RECORD_KEYS or key.startswith("_"):
                continue
            if value is None:
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
    candidate = Path(raw_path.strip() or "logs/logs.txt")
    if candidate.is_absolute():
        return candidate
    return BASE_DIR / candidate


def _coerce_level(level_raw: Any) -> int:
    level_name = str(level_raw or "INFO").strip().upper()
    return getattr(logging, level_name, logging.INFO)


def _use_json_format() -> bool:
    fmt = str(getattr(settings, "LOG_FORMAT", "") or "").strip().lower()
    if fmt in {"json", "text"}:
        return fmt == "json"
    return bool(getattr(settings, "LOG_JSON", True))


def _log_to_console() -> bool:
    if hasattr(settings, "LOG_TO_CONSOLE"):
        return bool(settings.LOG_TO_CONSOLE)
    return bool(getattr(settings, "LOG_TO_STDOUT", True))


def _log_to_file() -> bool:
    return bool(getattr(settings, "LOG_TO_FILE", True))


def _retention_days() -> int:
    try:
        days = int(getattr(settings, "LOG_RETENTION_DAYS", 1))
    except (TypeError, ValueError):
        return 1
    return max(1, min(days, 365))


def _rotated_log_pattern(log_path: Path) -> str:
    return f"{log_path.name}."


def cleanup_rotated_logs(log_path: Path, *, retention_days: int | None = None) -> int:
    """Delete rotated application log files older than retention_days. Returns deleted count."""
    days = retention_days if retention_days is not None else _retention_days()
    days = max(1, min(int(days), 365))
    cutoff = time.time() - (days * 86400)
    prefix = _rotated_log_pattern(log_path)
    deleted = 0
    if not log_path.parent.exists():
        return deleted
    for candidate in log_path.parent.iterdir():
        if not candidate.is_file() or candidate == log_path:
            continue
        if not candidate.name.startswith(prefix):
            continue
        try:
            if candidate.stat().st_mtime < cutoff:
                candidate.unlink()
                deleted += 1
        except OSError:
            logging.getLogger(__name__).warning(
                "log_cleanup_failed",
                extra={"path": str(candidate)},
                exc_info=True,
            )
    return deleted


class AppTimedRotatingFileHandler(TimedRotatingFileHandler):
    """Daily rotation with retention cleanup after each rollover."""

    def __init__(self, log_path: Path, *, retention_days: int, level: int, formatter: logging.Formatter):
        log_path.parent.mkdir(parents=True, exist_ok=True)
        super().__init__(
            filename=str(log_path),
            when="midnight",
            interval=1,
            backupCount=0,
            encoding="utf-8",
            utc=False,
        )
        self._retention_days = retention_days
        self.setLevel(level)
        self.setFormatter(formatter)

    def doRollover(self) -> None:
        super().doRollover()
        cleanup_rotated_logs(Path(self.baseFilename), retention_days=self._retention_days)


def reset_logging_for_tests() -> None:
    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        if getattr(handler, "_languageapp_handler", False):
            root_logger.removeHandler(handler)
            try:
                handler.close()
            except Exception:
                pass
    for flt in list(root_logger.filters):
        if getattr(flt, "_languageapp_filter", False):
            root_logger.removeFilter(flt)
    configure_logging._configured = False
    if hasattr(configure_logging, "_log_path"):
        delattr(configure_logging, "_log_path")


def configure_logging() -> Path | None:
    if getattr(configure_logging, "_configured", False):
        return getattr(configure_logging, "_log_path", None)

    root_logger = logging.getLogger()
    level = _coerce_level(getattr(settings, "LOG_LEVEL", "INFO"))
    root_logger.setLevel(level)

    for handler in list(root_logger.handlers):
        if getattr(handler, "_languageapp_handler", False):
            root_logger.removeHandler(handler)

    for flt in list(root_logger.filters):
        if getattr(flt, "_languageapp_filter", False):
            root_logger.removeFilter(flt)

    context_filter = ContextFilter()
    context_filter._languageapp_filter = True  # type: ignore[attr-defined]
    sensitive_filter = SensitiveDataFilter()
    sensitive_filter._languageapp_filter = True  # type: ignore[attr-defined]
    root_logger.addFilter(context_filter)
    root_logger.addFilter(sensitive_filter)

    formatter: logging.Formatter = JsonFormatter() if _use_json_format() else KeyValueFormatter()
    log_path: Path | None = None

    if _log_to_file():
        log_path = _resolve_log_path(getattr(settings, "LOG_FILE_PATH", "logs/logs.txt"))
        file_handler = AppTimedRotatingFileHandler(
            log_path,
            retention_days=_retention_days(),
            level=level,
            formatter=formatter,
        )
        file_handler._languageapp_handler = True  # type: ignore[attr-defined]
        file_handler.addFilter(context_filter)
        file_handler.addFilter(sensitive_filter)
        root_logger.addHandler(file_handler)
        cleanup_rotated_logs(log_path)

    if _log_to_console():
        stream_handler = logging.StreamHandler()
        stream_handler._languageapp_handler = True  # type: ignore[attr-defined]
        stream_handler.setLevel(level)
        stream_handler.setFormatter(formatter)
        stream_handler.addFilter(context_filter)
        stream_handler.addFilter(sensitive_filter)
        root_logger.addHandler(stream_handler)

    for noisy_logger in ("uvicorn.access", "httpx"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)

    configure_logging._configured = True
    configure_logging._log_path = log_path

    root_logger.info(
        "Logging configured",
        extra={
            "log_file": str(log_path) if log_path else None,
            "log_level": logging.getLevelName(level),
            "log_format": "json" if _use_json_format() else "text",
            "log_retention_days": _retention_days(),
        },
    )
    return log_path


@contextmanager
def log_timing(
    logger: logging.Logger,
    event: str,
    *,
    level: int = logging.INFO,
    slow_ms: int | None = None,
    **fields: Any,
) -> Iterator[None]:
    start = time.perf_counter()
    logger.log(level, f"{event}_started", extra=fields)
    try:
        yield
    except Exception:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.exception(f"{event}_failed", extra={**fields, "duration_ms": duration_ms})
        raise
    else:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        extra = {**fields, "duration_ms": duration_ms}
        if slow_ms is not None and duration_ms >= slow_ms:
            logger.warning(f"{event}_slow", extra=extra)
        else:
            logger.log(level, f"{event}_complete", extra=extra)
