from __future__ import annotations

from backend.app.modules.agent.chat.prompt_assembly import PromptAssemblyService
from backend.app.modules.agent.core.context import AgentContext
from backend.app.modules.agent.core.stream_bus import StreamBus
from backend.app.modules.agent.db_session import (
    bind_turn_db_session,
    clear_turn_db_session,
    get_bound_db_session,
)
from backend.app.modules.agent.loop.runner import AgentLoopRunner
from backend.app.modules.agent.runtime.registry import get_tool_registry
from backend.app.modules.llm.service import create_task_client

DEFAULT_CHAT_TOOLS = [
    "ask_user",
    "search_knowledge",
    "save_to_notebook",
    "read_memory",
    "write_memory",
    "lookup_dictionary",
    "vision_ocr",
    "sandbox_eval",
    "rag_search",
]
DEFAULT_MAX_ITERATIONS = 8


class ChatPipeline:
    """Agentic chat loop: LLM + tools with pause/resume via ask_user."""

    def __init__(
        self,
        *,
        llm_task: str = "tutor_chat",
        source: str = "chat",
        prompt_assembly: PromptAssemblyService | None = None,
    ) -> None:
        self.llm_task = llm_task
        self.source = source
        self._prompt_assembly = prompt_assembly or PromptAssemblyService()

    async def run(self, context: AgentContext, bus: StreamBus) -> None:
        bound = get_bound_db_session(context)
        if bound is not None:
            await self._run_turn(context, bus, bound)
            return

        from backend.app.db.session import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            bind_turn_db_session(context, db)
            try:
                await self._run_turn(context, bus, db)
                await db.commit()
            except Exception:
                await db.rollback()
                raise
            finally:
                clear_turn_db_session(context)

    async def _run_turn(
        self,
        context: AgentContext,
        bus: StreamBus,
        db,
    ) -> None:
        system_prompt, llm_client = await self._prepare_turn(context, db)
        context.system_prompt = system_prompt

        enabled = context.enabled_tools
        if enabled is None:
            enabled = list(DEFAULT_CHAT_TOOLS)
        elif context.user_id:
            for tool_name in ("read_memory", "write_memory"):
                if tool_name not in enabled:
                    enabled.append(tool_name)
        tools = get_tool_registry().get_enabled(enabled)

        runner = AgentLoopRunner(source=self.source)
        max_iterations = int(
            context.config_overrides.get("max_iterations")
            or context.metadata.get("max_iterations")
            or DEFAULT_MAX_ITERATIONS
        )
        outcome = await runner.run(
            context=context,
            bus=bus,
            llm_client=llm_client,
            tools=tools,
            system_prompt=system_prompt,
            max_iterations=max_iterations,
        )
        if outcome.paused:
            context.metadata["agent_messages"] = outcome.messages
            if outcome.pending_tool_call:
                context.metadata["pending_tool_call"] = outcome.pending_tool_call
            if outcome.ask_user:
                context.metadata["ask_user"] = outcome.ask_user

    async def _prepare_turn(self, context: AgentContext, db):
        import asyncio

        system_prompt, llm_client = await asyncio.gather(
            self._prompt_assembly.build_system_prompt(context, db, llm_task=self.llm_task),
            create_task_client(self.llm_task),
        )
        return system_prompt, llm_client
