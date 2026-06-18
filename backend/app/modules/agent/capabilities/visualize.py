from __future__ import annotations

import json

from backend.app.modules.agent.core.context import AgentContext
from backend.app.modules.agent.core.protocols import BaseCapability
from backend.app.modules.agent.core.stream_bus import StreamBus
from backend.app.modules.agent.db_session import get_bound_db_session, resolve_agent_db
from backend.app.modules.extensions.visualize.service import get_visualize_service


class VisualizeCapability(BaseCapability):
    name = "visualize"
    description = "Grammar charts and learner progress visualizations."

    async def run(self, context: AgentContext, bus: StreamBus) -> None:
        import uuid

        user_id = context.user_id
        if not user_id:
            await bus.error("Progress visualization requires a signed-in learner.", source="visualize")
            return

        async with resolve_agent_db(context) as db:
            service = get_visualize_service()
            payload = await service.build_progress_charts(
                db, user_id=uuid.UUID(str(user_id)), level=context.cefr_level
            )
            if get_bound_db_session(context) is None:
                await db.commit()

        summary = (
            "Here is your current learning progress. "
            "The chart data is structured for the dashboard renderer."
        )
        await bus.content(summary, source="visualize")
        await bus.content(
            f"```json\n{json.dumps(payload, indent=2, ensure_ascii=False)}\n```",
            source="visualize",
            metadata={"chart_spec": payload},
        )
