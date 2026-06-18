from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

_TURN_KEY_PREFIX = "tutor:turn:"
_SESSION_KEY_PREFIX = "tutor:session:"


@dataclass
class StoredPausedTurnState:
    session_id: str
    capability: str
    cefr_level: str | None
    persona: str | None
    language: str
    enabled_tools: list[str] | None
    system_prompt: str
    agent_messages: list[dict[str, Any]]
    pause_question: str
    pending_tool_call: dict[str, str] | None = None
    ask_user: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StoredPausedTurnState:
        return cls(
            session_id=str(data["session_id"]),
            capability=str(data.get("capability") or "chat"),
            cefr_level=data.get("cefr_level"),
            persona=data.get("persona"),
            language=str(data.get("language") or "en"),
            enabled_tools=data.get("enabled_tools"),
            system_prompt=str(data.get("system_prompt") or ""),
            agent_messages=list(data.get("agent_messages") or []),
            pause_question=str(data.get("pause_question") or ""),
            pending_tool_call=data.get("pending_tool_call"),
            ask_user=data.get("ask_user"),
        )


@dataclass
class StoredTurnRecord:
    turn_id: str
    session_id: str
    user_id: str
    status: str = "running"
    seq: int = 0
    paused: StoredPausedTurnState | None = None
    user_message: str = ""
    conversation_history: list[dict[str, Any]] = field(default_factory=list)
    capability: str = "chat"
    language: str = "en"
    cefr_level: str | None = None
    persona: str | None = None

    def to_json(self) -> str:
        payload = {
            "turn_id": self.turn_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "status": self.status,
            "seq": self.seq,
            "paused": self.paused.to_dict() if self.paused else None,
            "user_message": self.user_message,
            "conversation_history": self.conversation_history,
            "capability": self.capability,
            "language": self.language,
            "cefr_level": self.cefr_level,
            "persona": self.persona,
        }
        return json.dumps(payload, ensure_ascii=False, default=str)

    @classmethod
    def from_json(cls, raw: str) -> StoredTurnRecord:
        data = json.loads(raw)
        paused_raw = data.get("paused")
        paused = (
            StoredPausedTurnState.from_dict(paused_raw)
            if isinstance(paused_raw, dict)
            else None
        )
        return cls(
            turn_id=str(data["turn_id"]),
            session_id=str(data["session_id"]),
            user_id=str(data["user_id"]),
            status=str(data.get("status") or "running"),
            seq=int(data.get("seq") or 0),
            paused=paused,
            user_message=str(data.get("user_message") or ""),
            conversation_history=list(data.get("conversation_history") or []),
            capability=str(data.get("capability") or "chat"),
            language=str(data.get("language") or "en"),
            cefr_level=data.get("cefr_level"),
            persona=data.get("persona"),
        )


class TurnStateStore(Protocol):
    async def acquire_session(self, session_id: str, turn_id: str, *, ttl_seconds: int) -> bool: ...

    async def release_session(self, session_id: str, turn_id: str) -> None: ...

    async def save_turn(self, record: StoredTurnRecord) -> None: ...

    async def get_turn(self, turn_id: str) -> StoredTurnRecord | None: ...

    async def get_session_turn_id(self, session_id: str) -> str | None: ...

    async def delete_turn(self, turn_id: str) -> None: ...


def _turn_ttl_seconds(status: str) -> int:
    if status == "paused":
        return settings.TUTOR_TURN_PAUSED_TTL_SECONDS
    return settings.TUTOR_TURN_RUNNING_TTL_SECONDS


class InMemoryTurnStateStore:
    def __init__(self) -> None:
        self._turns: dict[str, StoredTurnRecord] = {}
        self._session_turn: dict[str, str] = {}

    async def acquire_session(self, session_id: str, turn_id: str, *, ttl_seconds: int) -> bool:
        del ttl_seconds
        existing = self._session_turn.get(session_id)
        if existing and existing != turn_id:
            turn = self._turns.get(existing)
            if turn and turn.status == "running":
                return False
        self._session_turn[session_id] = turn_id
        return True

    async def release_session(self, session_id: str, turn_id: str) -> None:
        if self._session_turn.get(session_id) == turn_id:
            self._session_turn.pop(session_id, None)

    async def save_turn(self, record: StoredTurnRecord) -> None:
        self._turns[record.turn_id] = record
        self._session_turn[record.session_id] = record.turn_id

    async def get_turn(self, turn_id: str) -> StoredTurnRecord | None:
        return self._turns.get(turn_id)

    async def get_session_turn_id(self, session_id: str) -> str | None:
        return self._session_turn.get(session_id)

    async def delete_turn(self, turn_id: str) -> None:
        record = self._turns.pop(turn_id, None)
        if record and self._session_turn.get(record.session_id) == turn_id:
            self._session_turn.pop(record.session_id, None)


class RedisTurnStateStore:
    def __init__(self, redis_client: Any) -> None:
        self._redis = redis_client

    def _turn_key(self, turn_id: str) -> str:
        return f"{_TURN_KEY_PREFIX}{turn_id}"

    def _session_key(self, session_id: str) -> str:
        return f"{_SESSION_KEY_PREFIX}{session_id}"

    async def acquire_session(self, session_id: str, turn_id: str, *, ttl_seconds: int) -> bool:
        acquired = await self._redis.set(
            self._session_key(session_id),
            turn_id,
            nx=True,
            ex=ttl_seconds,
        )
        if acquired:
            return True

        existing_turn_id = await self._redis.get(self._session_key(session_id))
        if not existing_turn_id:
            return await self.acquire_session(session_id, turn_id, ttl_seconds=ttl_seconds)

        if existing_turn_id == turn_id:
            await self._redis.expire(self._session_key(session_id), ttl_seconds)
            return True

        existing = await self.get_turn(str(existing_turn_id))
        if existing and existing.status == "running":
            return False

        await self._redis.set(
            self._session_key(session_id),
            turn_id,
            ex=ttl_seconds,
        )
        return True

    async def release_session(self, session_id: str, turn_id: str) -> None:
        key = self._session_key(session_id)
        current = await self._redis.get(key)
        if current == turn_id:
            await self._redis.delete(key)

    async def save_turn(self, record: StoredTurnRecord) -> None:
        ttl = _turn_ttl_seconds(record.status)
        await self._redis.set(
            self._turn_key(record.turn_id),
            record.to_json(),
            ex=ttl,
        )
        await self._redis.set(
            self._session_key(record.session_id),
            record.turn_id,
            ex=ttl,
        )

    async def get_turn(self, turn_id: str) -> StoredTurnRecord | None:
        raw = await self._redis.get(self._turn_key(turn_id))
        if not raw:
            return None
        try:
            return StoredTurnRecord.from_json(str(raw))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            logger.warning("Corrupt tutor turn state for %s", turn_id)
            return None

    async def get_session_turn_id(self, session_id: str) -> str | None:
        value = await self._redis.get(self._session_key(session_id))
        return str(value) if value else None

    async def delete_turn(self, turn_id: str) -> None:
        record = await self.get_turn(turn_id)
        await self._redis.delete(self._turn_key(turn_id))
        if record:
            await self.release_session(record.session_id, turn_id)


_store: TurnStateStore | None = None


def get_turn_state_store() -> TurnStateStore:
    global _store
    if _store is not None:
        return _store

    try:
        from backend.app.core.redis import get_redis

        get_redis()
        _store = RedisTurnStateStore(get_redis())
        logger.info("Tutor turn state store: Redis")
    except Exception:
        logger.warning("Redis unavailable for tutor turn state; using in-memory store", exc_info=True)
        _store = InMemoryTurnStateStore()
    return _store


def reset_turn_state_store_for_tests(store: TurnStateStore | None = None) -> None:
    global _store
    _store = store
