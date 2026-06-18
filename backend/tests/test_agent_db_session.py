from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from backend.app.modules.agent.core.context import AgentContext
from backend.app.modules.agent.db_session import (
    bind_turn_db_session,
    clear_turn_db_session,
    get_bound_db_session,
    resolve_agent_db,
)
from sqlalchemy.ext.asyncio import AsyncSession


def _session_mock() -> MagicMock:
    return MagicMock(spec=AsyncSession)


def test_bind_and_get_turn_db_session() -> None:
    context = AgentContext()
    db = _session_mock()
    bind_turn_db_session(context, db)
    assert get_bound_db_session(context) is db
    clear_turn_db_session(context)
    assert get_bound_db_session(context) is None


def test_resolve_agent_db_reuses_bound_session() -> None:
    async def _run() -> None:
        context = AgentContext()
        db = _session_mock()
        bind_turn_db_session(context, db)
        async with resolve_agent_db(context) as resolved:
            assert resolved is db

    asyncio.run(_run())


def test_resolve_agent_db_opens_fresh_session_when_unbound() -> None:
    async def _run() -> None:
        context = AgentContext()
        session = AsyncMock()

        class _SessionCtx:
            async def __aenter__(self):
                return session

            async def __aexit__(self, *args):
                return False

        with patch(
            "backend.app.db.session.AsyncSessionLocal",
            return_value=_SessionCtx(),
        ):
            async with resolve_agent_db(context) as resolved:
                assert resolved is session

    asyncio.run(_run())
