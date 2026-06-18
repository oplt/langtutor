from __future__ import annotations

from backend.app.modules.prompt.assembler import build_task_system_prompt


def build_tutor_system_prompt(
    *,
    base_prompt: str,
    cefr_level: str | None,
    language: str,
    ui_language: str = "en",
    task: str = "tutor_chat",
) -> str:
    """Build tutor system prompt from YAML packs (settings override optional)."""
    return build_task_system_prompt(
        task=task,
        ui_language=ui_language or language,
        cefr_level=cefr_level,
        practice_language="nl",
        settings_override=base_prompt,
    )
