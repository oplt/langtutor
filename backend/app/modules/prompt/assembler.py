from __future__ import annotations

from backend.app.modules.prompt.manager import TASK_TO_PACK, get_prompt_manager, normalize_language


def build_system_prompt(
    *,
    pack: str,
    ui_language: str = "en",
    cefr_level: str | None = None,
    practice_language: str = "nl",
    settings_override: str = "",
) -> str:
    """Assemble a system prompt from a YAML pack + runtime context."""
    manager = get_prompt_manager()
    prompts = manager.load_pack(pack, ui_language)

    parts: list[str] = []

    override = settings_override.strip()
    if override:
        parts.append(override)

    base = manager.get_text(prompts, "system", "base")
    if base:
        parts.append(base)

    loop = manager.get_text(prompts, "system", "loop")
    if loop:
        parts.append(loop)

    ask_user = manager.get_text(prompts, "system", "ask_user")
    if ask_user:
        parts.append(ask_user)

    if cefr_level:
        level_key = cefr_level.upper()
        level_text = manager.get_text(prompts, "cefr", level_key)
        if not level_text:
            level_text = manager.get_text(prompts, "cefr", "default")
        if level_text:
            parts.append(f"Learner CEFR level: {level_key}.\n{level_text}")

    locale_note = manager.get_text(prompts, "runtime", "locale")
    if locale_note:
        parts.append(
            locale_note.format(
                practice_language=practice_language,
                ui_language=normalize_language(ui_language),
            )
        )
    else:
        parts.append(
            f"Practice language: {practice_language}. "
            f"UI / explanation language: {normalize_language(ui_language)}."
        )

    return "\n\n".join(part.strip() for part in parts if part and part.strip())


def build_task_system_prompt(
    *,
    task: str,
    ui_language: str = "en",
    cefr_level: str | None = None,
    practice_language: str = "nl",
    settings_override: str = "",
) -> str:
    pack = TASK_TO_PACK.get(task, task)
    return build_system_prompt(
        pack=pack,
        ui_language=ui_language,
        cefr_level=cefr_level,
        practice_language=practice_language,
        settings_override=settings_override,
    )
