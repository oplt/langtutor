from __future__ import annotations

import pytest
from backend.app.modules.tutor.turn_state_store import (
    InMemoryTurnStateStore,
    StoredPausedTurnState,
    StoredTurnRecord,
)


@pytest.fixture
def store() -> InMemoryTurnStateStore:
    return InMemoryTurnStateStore()


def _sample_record(
    *,
    turn_id: str = "turn-1",
    session_id: str = "sess-1",
    status: str = "running",
    paused: StoredPausedTurnState | None = None,
) -> StoredTurnRecord:
    return StoredTurnRecord(
        turn_id=turn_id,
        session_id=session_id,
        user_id="user-1",
        status=status,
        seq=3,
        paused=paused,
        user_message="hello",
        conversation_history=[{"role": "user", "content": "hello"}],
        capability="chat",
        language="en",
    )


def test_stored_turn_record_roundtrip_json() -> None:
    paused = StoredPausedTurnState(
        session_id="sess-1",
        capability="chat",
        cefr_level="A2",
        persona="coach",
        language="en",
        enabled_tools=["ask_user"],
        system_prompt="You are helpful.",
        agent_messages=[{"role": "assistant", "content": "Q?"}],
        pause_question="Which?",
        pending_tool_call={"id": "tc1", "name": "ask_user"},
        ask_user={"questions": [{"id": "q1", "prompt": "Which?"}]},
    )
    original = _sample_record(status="paused", paused=paused)
    restored = StoredTurnRecord.from_json(original.to_json())
    assert restored.turn_id == original.turn_id
    assert restored.status == "paused"
    assert restored.paused is not None
    assert restored.paused.pause_question == "Which?"
    assert restored.paused.ask_user == paused.ask_user


def test_acquire_session_blocks_running_turn(store: InMemoryTurnStateStore) -> None:
    async def _run() -> None:
        first = _sample_record(turn_id="turn-a", session_id="sess-x")
        await store.save_turn(first)
        assert await store.acquire_session("sess-x", "turn-b", ttl_seconds=60) is False

        first.status = "completed"
        await store.save_turn(first)
        assert await store.acquire_session("sess-x", "turn-b", ttl_seconds=60) is True

    import asyncio

    asyncio.run(_run())


def test_release_session_only_when_turn_matches(store: InMemoryTurnStateStore) -> None:
    async def _run() -> None:
        record = _sample_record()
        await store.save_turn(record)
        await store.release_session("sess-1", "other-turn")
        assert await store.get_session_turn_id("sess-1") == "turn-1"
        await store.release_session("sess-1", "turn-1")
        assert await store.get_session_turn_id("sess-1") is None

    import asyncio

    asyncio.run(_run())


def test_paused_turn_persists_across_store_instances(store: InMemoryTurnStateStore) -> None:
    async def _run() -> None:
        paused = StoredPausedTurnState(
            session_id="sess-1",
            capability="chat",
            cefr_level=None,
            persona=None,
            language="en",
            enabled_tools=None,
            system_prompt="sys",
            agent_messages=[],
            pause_question="Pick one",
        )
        record = _sample_record(status="paused", paused=paused)
        await store.save_turn(record)

        loaded = await store.get_turn("turn-1")
        assert loaded is not None
        assert loaded.status == "paused"
        assert loaded.paused is not None
        assert loaded.paused.pause_question == "Pick one"

    import asyncio

    asyncio.run(_run())
