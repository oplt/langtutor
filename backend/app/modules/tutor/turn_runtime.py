from __future__ import annotations

import asyncio
import logging
from typing import Any

from uuid import uuid4

from backend.app.modules.agent.core.context import AgentContext
from backend.app.modules.agent.core.stream import StreamEventType
from backend.app.modules.agent.service import get_orchestrator
from backend.app.modules.agent.tools.ask_user_payload import (
    AskUserPayload,
    AskUserQuestion,
    format_ask_user_tool_result,
)
from backend.app.modules.tutor.context_factory import build_agent_context
from backend.app.modules.tutor.persistence import finalize_tutor_turn_lifecycle
from backend.app.modules.tutor.schemas import TutorMessageIn
from backend.app.modules.tutor.turn_executor import iter_orchestrator_events
from backend.app.modules.tutor.turn_models import (
    PausedTurnState,
    TurnRecord,
    record_from_stored,
    record_to_stored,
)
from backend.app.modules.tutor.turn_persistence_adapter import persist_turn_fragment
from backend.app.modules.tutor.turn_protocol import EventSender, build_event_envelope
from backend.app.modules.tutor.turn_state_store import get_turn_state_store

logger = logging.getLogger(__name__)


class TutorTurnRuntime:
    def __init__(self) -> None:
        self._local_tasks: dict[str, asyncio.Task[None]] = {}
        self._orchestrator = get_orchestrator()
        self._store = get_turn_state_store()

    async def _load_record(self, turn_id: str) -> TurnRecord | None:
        stored = await self._store.get_turn(turn_id)
        if stored is None:
            return None
        return record_from_stored(stored, task=self._local_tasks.get(turn_id))

    async def _save_record(self, record: TurnRecord) -> None:
        await self._store.save_turn(record_to_stored(record))

    async def get_turn(self, turn_id: str) -> TurnRecord | None:
        return await self._load_record(turn_id)

    async def active_turn_for_session(self, session_id: str) -> TurnRecord | None:
        turn_id = await self._store.get_session_turn_id(session_id)
        if not turn_id:
            return None
        turn = await self._load_record(turn_id)
        if turn and turn.status == "running":
            return turn
        return None

    async def start_turn(
        self,
        *,
        payload: TutorMessageIn,
        user_id: str,
        send: EventSender,
    ) -> TurnRecord:
        from backend.app.core.config import settings

        session_id = payload.session_id or str(uuid4())
        active = await self.active_turn_for_session(session_id)
        if active:
            raise RuntimeError("turn_busy")

        turn_id = str(uuid4())
        acquired = await self._store.acquire_session(
            session_id,
            turn_id,
            ttl_seconds=settings.TUTOR_TURN_RUNNING_TTL_SECONDS,
        )
        if not acquired:
            raise RuntimeError("turn_busy")

        context = build_agent_context(
            payload,
            user_id=user_id,
            turn_id=turn_id,
            session_id=session_id,
        )
        record = TurnRecord(
            turn_id=turn_id,
            session_id=session_id,
            user_id=user_id,
            user_message=context.user_message,
            conversation_history=payload.conversation_history or [],
            capability=context.active_capability or "chat",
            language=context.language or "en",
            cefr_level=context.cefr_level,
            persona=str(context.metadata.get("persona") or "") or None,
        )
        await self._save_record(record)

        await send(
            {
                "type": "turn_started",
                "turn_id": turn_id,
                "session_id": session_id,
            }
        )

        task = asyncio.create_task(
            self._execute_turn(
                record=record,
                context=context,
                send=send,
            )
        )
        record.task = task
        self._local_tasks[turn_id] = task
        return record

    async def submit_user_reply(
        self,
        *,
        turn_id: str,
        reply: str,
        user_id: str,
        send: EventSender,
        answers: list[dict[str, str]] | None = None,
    ) -> None:
        record = await self._load_record(turn_id)
        if record is None:
            raise RuntimeError("turn_not_found")
        if record.user_id != user_id:
            raise RuntimeError("turn_forbidden")
        if record.status != "paused" or record.paused is None:
            raise RuntimeError("turn_not_paused")
        local_task = self._local_tasks.get(turn_id)
        if local_task and not local_task.done():
            raise RuntimeError("turn_busy")

        paused = record.paused
        record.status = "running"
        await self._save_record(record)

        ask_payload: AskUserPayload | None = None
        if paused.ask_user and isinstance(paused.ask_user.get("questions"), list):
            rebuilt = []
            for raw in paused.ask_user["questions"]:
                if isinstance(raw, dict):
                    rebuilt.append(
                        AskUserQuestion(
                            id=str(raw.get("id") or ""),
                            prompt=str(raw.get("prompt") or raw.get("question") or ""),
                        )
                    )
            if rebuilt:
                ask_payload = AskUserPayload(
                    questions=tuple(rebuilt),
                    intro=paused.ask_user.get("intro"),
                )

        tool_content = format_ask_user_tool_result(
            reply=reply,
            answers=answers,
            payload=ask_payload,
        )

        resume_messages = list(paused.agent_messages)
        pending = paused.pending_tool_call or {}
        tool_call_id = str(pending.get("id") or "ask_user")
        tool_name = str(pending.get("name") or "ask_user")
        resume_messages.append(
            {
                "role": "tool",
                "content": tool_content,
                "tool_call_id": tool_call_id,
                "name": tool_name,
            }
        )

        context = AgentContext(
            session_id=paused.session_id,
            user_id=user_id,
            user_message="",
            conversation_history=[],
            enabled_tools=paused.enabled_tools,
            active_capability=paused.capability,
            language=paused.language,
            cefr_level=paused.cefr_level,
            system_prompt=paused.system_prompt,
            metadata={
                "turn_id": turn_id,
                "resume_messages": resume_messages,
                "persona": paused.persona,
            },
        )
        record.paused = None
        task = asyncio.create_task(
            self._execute_turn(record=record, context=context, send=send)
        )
        record.task = task
        self._local_tasks[turn_id] = task

    async def cancel_turn(self, turn_id: str, *, user_id: str) -> None:
        record = await self._load_record(turn_id)
        if record is None:
            raise RuntimeError("turn_not_found")
        if record.user_id != user_id:
            raise RuntimeError("turn_forbidden")

        record.status = "cancelled"
        await self._save_record(record)

        local_task = self._local_tasks.get(turn_id)
        if local_task and not local_task.done():
            local_task.cancel()
            try:
                await local_task
            except asyncio.CancelledError:
                pass

        await self._store.release_session(record.session_id, turn_id)

    async def _is_turn_cancelled(self, turn_id: str) -> bool:
        stored = await self._store.get_turn(turn_id)
        return stored is not None and stored.status == "cancelled"

    async def _execute_turn(
        self,
        *,
        record: TurnRecord,
        context: AgentContext,
        send: EventSender,
    ) -> None:
        paused_state: PausedTurnState | None = None
        events_fragment: list[dict[str, Any]] = []
        assistant_reply_fragment_parts: list[str] = []
        from backend.app.db.session import AsyncSessionLocal
        from backend.app.modules.agent.db_session import bind_turn_db_session, clear_turn_db_session

        async with AsyncSessionLocal() as db:
            bind_turn_db_session(context, db)
            try:
                async for event in iter_orchestrator_events(self._orchestrator, context):
                    if await self._is_turn_cancelled(record.turn_id):
                        record.status = "cancelled"
                        await self._save_record(record)
                        await send(
                            {
                                "type": "turn_cancelled",
                                "turn_id": record.turn_id,
                                "session_id": record.session_id,
                            }
                        )
                        return

                    record.seq += 1
                    if event.type in {StreamEventType.CONTENT, StreamEventType.CONTENT_DELTA} and event.content:
                        assistant_reply_fragment_parts.append(event.content)

                    events_fragment.append(
                        {
                            "seq": record.seq,
                            "type": event.type.value,
                            "source": event.source,
                            "content": event.content,
                            "metadata": event.metadata,
                        }
                    )

                    await send(build_event_envelope(record, event))
                    if event.type == StreamEventType.ASK_USER:
                        meta = event.metadata or {}
                        paused_state = PausedTurnState(
                            session_id=record.session_id,
                            capability=context.active_capability or "chat",
                            cefr_level=context.cefr_level,
                            persona=str(context.metadata.get("persona") or "") or None,
                            language=context.language,
                            enabled_tools=context.enabled_tools,
                            system_prompt=context.system_prompt,
                            agent_messages=list(meta.get("agent_messages") or []),
                            pause_question=event.content,
                            pending_tool_call=meta.get("pending_tool_call"),
                            ask_user=meta.get("ask_user"),
                        )

                if paused_state:
                    record.status = "paused"
                    record.paused = paused_state
                    await self._save_record(record)
                    payload: dict[str, Any] = {
                        "type": "turn_paused",
                        "turn_id": record.turn_id,
                        "session_id": record.session_id,
                        "question": paused_state.pause_question,
                    }
                    if paused_state.ask_user:
                        payload["ask_user"] = paused_state.ask_user
                    await persist_turn_fragment(
                        record=record,
                        events_fragment=events_fragment,
                        assistant_reply_fragment="".join(assistant_reply_fragment_parts),
                        status="paused",
                        paused=True,
                        pause_question=paused_state.pause_question,
                    )
                    await send(payload)
                else:
                    record.status = "completed"
                    await self._save_record(record)
                    await send(
                        {
                            "type": "turn_done",
                            "turn_id": record.turn_id,
                            "session_id": record.session_id,
                        }
                    )
                    await finalize_tutor_turn_lifecycle(
                        context=context,
                        user_id=record.user_id,
                        turn_id=record.turn_id,
                        session_id=record.session_id,
                        capability=record.capability,
                        language=record.language,
                        cefr_level=record.cefr_level,
                        persona=record.persona,
                        user_message=record.user_message,
                        conversation_history=record.conversation_history,
                        seq=record.seq,
                        status="completed",
                        events_fragment=events_fragment,
                        assistant_reply_fragment="".join(assistant_reply_fragment_parts),
                        paused=False,
                        pause_question=None,
                    )
                await db.commit()
            except asyncio.CancelledError:
                record.status = "cancelled"
                await self._save_record(record)
                await persist_turn_fragment(
                    record=record,
                    events_fragment=events_fragment,
                    assistant_reply_fragment="".join(assistant_reply_fragment_parts),
                    status="cancelled",
                    paused=False,
                    pause_question=None,
                )
                await send(
                    {
                        "type": "turn_cancelled",
                        "turn_id": record.turn_id,
                        "session_id": record.session_id,
                    }
                )
                await db.rollback()
                raise
            except Exception as exc:
                logger.exception("Turn %s failed", record.turn_id)
                record.status = "error"
                await self._save_record(record)
                await persist_turn_fragment(
                    record=record,
                    events_fragment=events_fragment,
                    assistant_reply_fragment="".join(assistant_reply_fragment_parts),
                    status="error",
                    paused=False,
                    pause_question=None,
                )
                await send(
                    {
                        "type": "error",
                        "turn_id": record.turn_id,
                        "message": str(exc),
                    }
                )
                await db.rollback()
            finally:
                clear_turn_db_session(context)
                self._local_tasks.pop(record.turn_id, None)
                if record.status != "paused":
                    await self._store.release_session(record.session_id, record.turn_id)


_runtime: TutorTurnRuntime | None = None


def get_tutor_turn_runtime() -> TutorTurnRuntime:
    global _runtime
    if _runtime is None:
        _runtime = TutorTurnRuntime()
    return _runtime
