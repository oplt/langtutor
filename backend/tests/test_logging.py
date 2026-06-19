from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.app.core import logging as logging_module
from backend.app.core.logging import (
    cleanup_rotated_logs,
    configure_logging,
    redact_sensitive_value,
    redact_url,
    reset_logging_for_tests,
    set_log_context,
)


@pytest.fixture(autouse=True)
def _reset_logging():
    reset_logging_for_tests()
    yield
    reset_logging_for_tests()


def test_redact_sensitive_values():
    assert redact_sensitive_value("password", "secret123") == "***REDACTED***"
    assert redact_sensitive_value("api_key", "sk-live-abc") == "***REDACTED***"
    assert redact_sensitive_value("user_id", "abc-123") == "abc-123"
    assert redact_url("redis://:supersecret@127.0.0.1:6379/0") == "redis://:***@127.0.0.1:6379/0"


def test_configure_logging_writes_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    log_file = tmp_path / "logs.txt"
    monkeypatch.setenv("LOG_FILE_PATH", str(log_file))
    monkeypatch.setenv("LOG_TO_FILE", "true")
    monkeypatch.setenv("LOG_TO_CONSOLE", "false")
    monkeypatch.setenv("LOG_FORMAT", "text")
    monkeypatch.setenv("LOG_LEVEL", "INFO")

    with patch("backend.app.core.logging.settings") as mock_settings:
        mock_settings.LOG_LEVEL = "INFO"
        mock_settings.LOG_FILE_PATH = str(log_file)
        mock_settings.LOG_TO_FILE = True
        mock_settings.LOG_TO_CONSOLE = False
        mock_settings.LOG_TO_STDOUT = False
        mock_settings.LOG_FORMAT = "text"
        mock_settings.LOG_JSON = False
        mock_settings.LOG_RETENTION_DAYS = 1
        configure_logging()

    logger = logging.getLogger("test.logger")
    logger.info("hello from test", extra={"request_id": "req-1"})

    content = log_file.read_text(encoding="utf-8")
    assert "hello from test" in content
    assert "request_id='req-1'" in content or '"request_id":"req-1"' in content


def test_invalid_retention_falls_back_to_default():
    with patch("backend.app.core.logging.settings") as mock_settings:
        mock_settings.LOG_RETENTION_DAYS = "not-a-number"
        assert logging_module._retention_days() == 1


def test_cleanup_only_deletes_rotated_app_logs(tmp_path: Path):
    active = tmp_path / "logs.txt"
    active.write_text("active", encoding="utf-8")
    old_rotated = tmp_path / "logs.txt.2020-01-01"
    old_rotated.write_text("old", encoding="utf-8")
    os.utime(old_rotated, (1, 1))
    unrelated = tmp_path / "other.txt"
    unrelated.write_text("keep", encoding="utf-8")
    os.utime(unrelated, (1, 1))

    deleted = cleanup_rotated_logs(active, retention_days=1)
    assert deleted == 1
    assert active.exists()
    assert not old_rotated.exists()
    assert unrelated.exists()


def test_request_id_middleware_and_error_logging(tmp_path: Path):
    from backend.app.main import create_app

    app = create_app()

    @app.get("/boom")
    async def boom():
        raise RuntimeError("boom")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/boom", headers={"X-Request-ID": "trace-me"})
    assert response.status_code == 500
    assert response.headers.get("x-request-id") == "trace-me"
    assert response.json()["request_id"] == "trace-me"


def test_http_exception_not_double_logged():
    from backend.app.main import create_app

    app = create_app()

    @app.get("/missing")
    async def missing():
        raise HTTPException(status_code=404, detail="missing")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/missing")
    assert response.status_code == 404


def test_sensitive_filter_redacts_log_record():
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="token=abc",
        args=(),
        exc_info=None,
    )
    record.api_key = "secret-value"
    flt = logging_module.SensitiveDataFilter()
    assert flt.filter(record) is True
    assert record.api_key == "***REDACTED***"


def test_log_context_available_in_formatter():
    set_log_context(request_id="rid-42", trace_id="tid-42")
    formatter = logging_module.JsonFormatter()
    record = logging.LogRecord(
        name="ctx",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="with context",
        args=(),
        exc_info=None,
    )
    logging_module.ContextFilter().filter(record)
    payload = json.loads(formatter.format(record))
    assert payload["request_id"] == "rid-42"
    assert payload["trace_id"] == "tid-42"
