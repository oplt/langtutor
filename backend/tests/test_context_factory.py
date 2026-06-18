from __future__ import annotations

from backend.app.core.logging import get_log_context, set_log_context
from backend.app.modules.tutor.context_factory import build_agent_context
from backend.app.modules.tutor.schemas import TutorMessageIn


def test_build_agent_context_propagates_log_context_ids() -> None:
    set_log_context(request_id="req-1", trace_id="trace-1")
    context = build_agent_context(
        TutorMessageIn(message="Hallo", capability="chat"),
        user_id="user-1",
    )
    assert context.metadata["request_id"] == "req-1"
    assert context.metadata["trace_id"] == "trace-1"
    assert context.metadata["turn_id"]
    set_log_context(request_id=None, trace_id=None)

    cleared = get_log_context()
    assert cleared["request_id"] is None
    assert cleared["trace_id"] is None
