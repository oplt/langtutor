from __future__ import annotations

import asyncio
import uuid

from backend.app.core.config import settings
from backend.app.modules.agent.chat.playbook import build_tutor_system_prompt
from backend.app.modules.agent.core.context import AgentContext
from backend.app.modules.agent.core.stream_bus import StreamBus
from backend.app.modules.agent.db_session import (
    bind_turn_db_session,
    clear_turn_db_session,
)
from backend.app.modules.agent.loop.runner import AgentLoopRunner
from backend.app.modules.agent.runtime.registry import get_tool_registry
from backend.app.modules.ai.service import AISettingsService
from backend.app.modules.llm.service import create_task_client
from backend.app.modules.persona.service import load_for_context as load_persona_context
from backend.app.modules.skills.service import get_playbook_text

# Tool set available for general tutor chat. Capabilities like deep_research
# can override this with a smaller list.
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
KNOWLEDGE_GROUNDING_MIN_SCORE = 0.35


class ChatPipeline:
    """Agentic chat loop: LLM + tools with pause/resume via ask_user."""

    def __init__(self, *, llm_task: str = "tutor_chat", source: str = "chat") -> None:
        self.llm_task = llm_task
        self.source = source

    async def run(self, context: AgentContext, bus: StreamBus) -> None:
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
        persona_name = str(context.metadata.get("persona") or "")
        cefr_level = context.cefr_level

        ai_settings, llm_client, memory_block = await asyncio.gather(
            AISettingsService().get_settings(effective=True),
            create_task_client(self.llm_task),
            self._load_memory_context(context, db),
        )

        persona_block, skill_playbook = await asyncio.to_thread(
            _load_sync_prompt_blocks,
            persona_name,
            cefr_level,
        )

        system_prompt = build_tutor_system_prompt(
            base_prompt=context.system_prompt or ai_settings.system_prompt,
            cefr_level=context.cefr_level,
            language=context.language or "nl",
            ui_language=str(context.metadata.get("ui_language") or context.language or "en"),
            task=self.llm_task,
        )

        if persona_block.strip():
            system_prompt = f"{system_prompt}\n\n{persona_block.strip()}"

        if memory_block:
            system_prompt = f"{system_prompt}\n\n## Learner memory\n{memory_block}"

        # Pedagogy layer: versioned tutor playbook per CEFR level (SKILL.md).
        if skill_playbook.strip():
            system_prompt = (
                f"{system_prompt}\n\n## Tutor playbook (CEFR)\n{skill_playbook.strip()}"
            )

        system_prompt = (
            f"{system_prompt}\n\n## Grounding (use the knowledge base)\n"
            "When you answer questions about Dutch word meanings, grammar rules, conjugations, "
            "or example usage, call the `search_knowledge` tool first (legacy alias: `rag`) "
            "and base your answer on the returned snippets. Each snippet includes a BM25 score — "
            f"prefer sources with score ≥ {KNOWLEDGE_GROUNDING_MIN_SCORE:.2f}. "
            "If all scores are below that threshold or the tool returns no matches, say the answer "
            "is uncertain and avoid inventing Dutch forms.\n\n"
            "When the learner wants to remember a word, call `save_to_notebook` with the lemma and a short note.\n\n"
            "When the learner asks to look up a Dutch word/translation or pronunciation hints, "
            "call `lookup_dictionary` first.\n"
            "When the learner asks to read/understand Dutch text from an image/photo, call `vision_ocr`.\n"
            "When the learner asks you to safely evaluate a small arithmetic expression, call `sandbox_eval`."
        )

        if settings.RAG_ENABLED:
            system_prompt = (
                f"{system_prompt}\n\n## Uploaded documents (user RAG)\n"
                "When the learner asks about their uploaded lesson notes, PDFs, or personal study files, "
                "call `rag_search` first and cite the returned snippets. "
                "Use `search_knowledge` (alias `rag`) for the global Dutch corpus — not for private uploads."
            )

        extra_prompt = str(context.metadata.get("extra_system_prompt") or "").strip()
        if extra_prompt:
            system_prompt = f"{system_prompt}\n\n{extra_prompt}"

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

    async def _load_memory_context(self, context: AgentContext, db) -> str:
        if not context.user_id:
            return ""
        from backend.app.modules.memory.context_loader import load_l3_memory_block

        return await load_l3_memory_block(
            db,
            user_id=uuid.UUID(str(context.user_id)),
            metadata=context.metadata,
        )


def _load_sync_prompt_blocks(persona_name: str, cefr_level: str | None) -> tuple[str, str]:
    return load_persona_context(persona_name), get_playbook_text(cefr_level)
