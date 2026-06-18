from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PluginManifest:
    id: str
    name: str
    description: str
    tool_names: tuple[str, ...]
    enabled_by_default: bool = True


BUILTIN_PLUGINS: tuple[PluginManifest, ...] = (
    PluginManifest(
        id="dutch-dictionary",
        name="Dutch Dictionary",
        description="Lookup lemmas and short glosses from the local Dutch corpus.",
        tool_names=("lookup_dictionary",),
    ),
    PluginManifest(
        id="forvo-pronunciation",
        name="Forvo Pronunciation",
        description="Fetch rule-based pronunciation hints for Dutch words.",
        tool_names=("pronunciation_forvo",),
    ),
)


def list_plugin_manifests() -> list[dict[str, Any]]:
    return [
        {
            "id": plugin.id,
            "name": plugin.name,
            "description": plugin.description,
            "tools": list(plugin.tool_names),
            "enabled_by_default": plugin.enabled_by_default,
        }
        for plugin in BUILTIN_PLUGINS
    ]


def default_plugin_tool_names() -> list[str]:
    names: list[str] = []
    for plugin in BUILTIN_PLUGINS:
        if plugin.enabled_by_default:
            names.extend(plugin.tool_names)
    return names
