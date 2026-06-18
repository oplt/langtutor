from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.modules.users.models import User
from backend.app.modules.agent.runtime.orchestrator import AgentOrchestrator
from backend.app.modules.auth.dependencies import get_current_user
from backend.app.modules.extensions.plugins.registry import list_plugin_manifests

router = APIRouter(prefix="/api/extensions/plugins", tags=["extensions-plugins"])


@router.get("")
async def list_plugins(user: User = Depends(get_current_user)):
    _ = user
    orchestrator = AgentOrchestrator()
    tools = set(orchestrator.list_tools())
    manifests = []
    for plugin in list_plugin_manifests():
        manifests.append(
            {
                **plugin,
                "tools_registered": [t for t in plugin["tools"] if t in tools],
            }
        )
    return {"plugins": manifests}
