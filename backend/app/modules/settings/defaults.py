from __future__ import annotations

from typing import Any

from backend.app.modules.settings.schemas import AISettingsSection, SettingsDoc


def build_default_settings_doc() -> dict[str, Any]:
    from backend.app.modules.ai.service import default_llm_settings

    return SettingsDoc(
        ai=AISettingsSection.model_validate(default_llm_settings())
    ).model_dump()
