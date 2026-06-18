from __future__ import annotations

from fastapi import APIRouter

from backend.app.modules.skills.schemas import SkillPlaybookContentOut, SkillPlaybookOut
from backend.app.modules.skills.service import get_playbook, list_playbooks
from backend.app.db.base import CEFRLevel


router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.get("/playbooks")
async def list_skill_playbooks():
    playbooks = list_playbooks()
    return {
        "playbooks": [
            SkillPlaybookOut(
                level=pb.level.value,
                title=pb.title,
                version=pb.version,
                updated_at=pb.updated_at,
                meta=pb.meta,
            )
            for pb in playbooks
        ]
    }


@router.get("/playbooks/{level}")
async def get_skill_playbook(level: CEFRLevel):
    pb = get_playbook(level)
    return SkillPlaybookContentOut(
        level=pb.level.value,
        title=pb.title,
        version=pb.version,
        content=pb.content,
    )
