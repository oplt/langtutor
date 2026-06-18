from __future__ import annotations

import time
import uuid

from backend.app.modules.memory.l3_cache import (
    L3_READ_CACHE_TTL_SECONDS,
    get_l3_read_cache,
    invalidate_l3_read_cache,
    reset_l3_read_cache_for_tests,
    set_l3_read_cache,
)


def test_l3_read_cache_roundtrip() -> None:
    reset_l3_read_cache_for_tests()
    user_id = uuid.uuid4()
    set_l3_read_cache(user_id, "### recent\n- hello")
    assert get_l3_read_cache(user_id) == "### recent\n- hello"


def test_l3_read_cache_expires(monkeypatch) -> None:
    reset_l3_read_cache_for_tests()
    user_id = uuid.uuid4()
    now = {"t": 1000.0}
    monkeypatch.setattr(time, "monotonic", lambda: now["t"])
    set_l3_read_cache(user_id, "cached")
    now["t"] += L3_READ_CACHE_TTL_SECONDS + 1
    assert get_l3_read_cache(user_id) is None


def test_invalidate_l3_read_cache() -> None:
    reset_l3_read_cache_for_tests()
    user_id = uuid.uuid4()
    set_l3_read_cache(user_id, "value")
    invalidate_l3_read_cache(user_id)
    assert get_l3_read_cache(user_id) is None
