"""Assemble layered system prompts for tutor chat turns."""

from __future__ import annotations

import asyncio

from backend.app.core.config import settings
from backend.app.modules.agent.chat.playbook import build_tutor_system_prompt
from backend.app.modules.agent.core.context import AgentContext
from backend.app.modules.ai.service import AISettingsService
from backend.app.modules.persona.service import load_for_context as load_persona_context
from backend.app.modules.skills.service import get_playbook_excerpt

KNOWLEDGE_GROUNDING_MIN_SCORE = 0.35

MEMORY_TOOL_GUIDANCE = (
    "## Learner memory\n"
    "Do not assume learner history is already loaded. When personalization, prior mistakes, "
    "or stated preferences would improve the answer, call `read_memory` first and use only "
    "what it returns. Skip the tool for generic explanations that do not need learner context."
)


class PromptAssemblyService:
    async def build_system_prompt(
        self,
        context: AgentContext,
        db,
        *,
        llm_task: str,
    ) -> str:
        persona_name = str(context.metadata.get("persona") or "")
        cefr_level = context.cefr_level

        ai_settings, _persona_and_playbook = await asyncio.gather(
            AISettingsService().get_settings(effective=True),
            asyncio.to_thread(_load_sync_prompt_blocks, persona_name, cefr_level),
        )
        persona_block, skill_playbook = _persona_and_playbook

        system_prompt = build_tutor_system_prompt(
            base_prompt=context.system_prompt or ai_settings.system_prompt,
            cefr_level=context.cefr_level,
            language=context.language or "nl",
            ui_language=str(context.metadata.get("ui_language") or context.language or "en"),
            task=llm_task,
        )

        if persona_block.strip():
            system_prompt = f"{system_prompt}\n\n{persona_block.strip()}"

        system_prompt = f"{system_prompt}\n\n{MEMORY_TOOL_GUIDANCE}"

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

        return system_prompt


def _load_sync_prompt_blocks(persona_name: str, cefr_level: str | None) -> tuple[str, str]:
    return load_persona_context(persona_name), get_playbook_excerpt(cefr_level)
