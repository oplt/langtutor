from __future__ import annotations

import json
import logging

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import JsonFormatter, configure_logging, reset_logging_for_tests
from backend.app.db.session import get_db, is_expected_client_error


@pytest.fixture(autouse=True)
def _reset_logging():
    reset_logging_for_tests()
    yield
    reset_logging_for_tests()


class _ListHandler(logging.Handler):
    def __init__(self, records: list[logging.LogRecord]) -> None:
        super().__init__()
        self._records = records

    def emit(self, record: logging.LogRecord) -> None:
        self._records.append(record)


@pytest.fixture
def log_records() -> list[logging.LogRecord]:
    reset_logging_for_tests()
    records: list[logging.LogRecord] = []
    handler = _ListHandler(records)
    handler.setFormatter(JsonFormatter())
    handler.setLevel(logging.DEBUG)
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(handler)
    yield records
    root.removeHandler(handler)


def test_is_expected_client_error():
    from fastapi import HTTPException
    from fastapi.exceptions import RequestValidationError

    from backend.app.core.exceptions import AppError

    assert is_expected_client_error(HTTPException(status_code=400, detail="bad")) is True
    assert is_expected_client_error(RequestValidationError(errors=[])) is True
    assert is_expected_client_error(AppError(code="x", message="y", status_code=400)) is True
    assert is_expected_client_error(RuntimeError("boom")) is False


def test_signup_invalid_email_returns_422(log_records: list[logging.LogRecord]):
    from backend.app.main import create_app

    client = TestClient(create_app(), raise_server_exceptions=False)
    response = client.post(
        "/auth/signup",
        json={"email": "ali", "password": "password123"},
        headers={"X-Request-ID": "val-req-1"},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "validation_error"
    assert body["request_id"] == "val-req-1"
    assert any(err.get("loc") == ["body", "email"] for err in body["error"]["details"])

    validation_logs = [r for r in log_records if r.getMessage() == "request_validation_error"]
    assert len(validation_logs) == 1
    record = validation_logs[0]
    assert record.levelno == logging.WARNING
    assert record.exc_info is None
    assert record.request_id == "val-req-1"
    assert record.status_code == 422
    assert record.method == "POST"
    assert record.path == "/auth/signup"
    assert any(err.get("loc") == ["body", "email"] for err in record.validation_errors)

    rollback_logs = [r for r in log_records if "Session rollback in get_db" in r.getMessage()]
    assert not any(r.levelno >= logging.WARNING and r.exc_info for r in rollback_logs)


def test_unexpected_db_error_logs_traceback(log_records: list[logging.LogRecord]):
    from backend.app.main import create_app

    app = create_app()

    @app.post("/test-db-boom")
    async def db_boom(db: AsyncSession = Depends(get_db)):
        raise RuntimeError("simulated database failure")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.post("/test-db-boom")

    assert response.status_code == 500

    rollback_logs = [
        r
        for r in log_records
        if r.name == "backend.app.db.session" and r.getMessage() == "Session rollback in get_db"
    ]
    assert len(rollback_logs) == 1
    assert rollback_logs[0].levelno == logging.WARNING
    assert rollback_logs[0].exc_info is not None

    unhandled_logs = [r for r in log_records if r.getMessage() == "Unhandled exception"]
    assert len(unhandled_logs) == 1
    assert unhandled_logs[0].exc_info is not None


def test_validation_log_is_json_formatted(log_records: list[logging.LogRecord]):
    from backend.app.main import create_app

    client = TestClient(create_app(), raise_server_exceptions=False)
    client.post("/auth/signup", json={"email": "not-an-email", "password": "password123"})

    validation_logs = [r for r in log_records if r.getMessage() == "request_validation_error"]
    assert validation_logs
    payload = json.loads(JsonFormatter().format(validation_logs[0]))
    assert payload["level"] == "WARNING"
    assert payload["message"] == "request_validation_error"
    assert payload["status_code"] == 422
    assert "exception" not in payload
