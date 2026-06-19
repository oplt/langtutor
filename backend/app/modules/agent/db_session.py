"""Turn-scoped database session helpers for the agent stack.

Session ownership contract
--------------------------
* One owner per tutor/agent turn opens the transactional ``AsyncSession``.
* HTTP tutor turns: ``TurnCoordinator.run_tutor_turn_with_session`` owns commit/rollback.
* WebSocket tutor turns: ``TutorTurnRuntime._execute_turn`` owns commit/rollback.
* ``ChatPipeline.run`` reuses a bound session when present; otherwise it opens its own
  short-lived session for standalone chat/RAG calls.
* Tools and services must call ``resolve_agent_db(context)`` instead of opening nested
  ``AsyncSessionLocal`` sessions when a turn session is already bound.
* Callers that bind a session must always ``clear_turn_db_session`` in ``finally``.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.modules.agent.core.context import AgentContext

DB_SESSION_KEY = "db_session"


def bind_turn_db_session(context: AgentContext, db: AsyncSession) -> None:
    context.metadata[DB_SESSION_KEY] = db


def clear_turn_db_session(context: AgentContext) -> None:
    context.metadata.pop(DB_SESSION_KEY, None)


def get_bound_db_session(context: AgentContext) -> AsyncSession | None:
    db = context.metadata.get(DB_SESSION_KEY)
    return db if isinstance(db, AsyncSession) else None


@asynccontextmanager
async def resolve_agent_db(context: AgentContext) -> AsyncIterator[AsyncSession]:
    """Reuse the turn-scoped session when the chat pipeline bound one."""
    bound = get_bound_db_session(context)
    if bound is not None:
        yield bound
        return

    from backend.app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        yield db
