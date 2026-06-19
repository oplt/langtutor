from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from backend.app.db.session import AsyncSessionLocal


def test_async_session_keeps_instances_after_commit():
    assert AsyncSessionLocal.kw.get("expire_on_commit") is False


def test_progress_summary_completes_with_bound_user_id():
    """Regression: progress summary must not touch expired ORM user attrs after flush."""
    from backend.app.modules.learning.api import progress_summary

    user_id = uuid.uuid4()
    user = MagicMock()
    user.id = user_id

    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one=MagicMock(return_value=10)),
            MagicMock(all=MagicMock(return_value=[])),
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
        ]
    )

    with (
        patch(
            "backend.app.modules.learning.api.get_cached_progress_summary",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "backend.app.modules.learning.api.ensure_words_seeded",
            new=AsyncMock(return_value=0),
        ),
        patch(
            "backend.app.modules.learning.api.level_counts",
            new=AsyncMock(return_value={}),
        ),
        patch(
            "backend.app.modules.learning.api.set_cached_progress_summary",
            new=AsyncMock(),
        ),
    ):
        summary = asyncio.run(progress_summary(user=user, db=db))

    assert summary.total_words == 10
    assert db.execute.await_count == 3
