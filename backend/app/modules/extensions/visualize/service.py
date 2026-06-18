from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.base import CEFRLevel
from backend.app.modules.learning.models import UserMasteryProgress, UserWordProgress, Word
from backend.app.modules.notebook.models import WordNotebookEntry


class VisualizeService:
    async def build_progress_charts(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        level: str | None = None,
    ) -> dict[str, Any]:
        words_by_level = await self._words_learned_by_level(db, user_id=user_id)
        mastery_summary = await self._mastery_summary(db, user_id=user_id)
        notebook_count = await self._notebook_count(db, user_id=user_id)

        focus_level = level or self._pick_focus_level(mastery_summary, words_by_level)
        grammar_radar = self._grammar_radar_from_mastery(mastery_summary, focus_level)

        return {
            "version": 1,
            "focus_level": focus_level,
            "charts": [
                {
                    "id": "words_by_level",
                    "type": "bar",
                    "title": "Words with SRS progress by CEFR level",
                    "labels": list(words_by_level.keys()),
                    "series": [
                        {
                            "name": "tracked_words",
                            "data": [words_by_level.get(lbl, 0) for lbl in words_by_level],
                        }
                    ],
                },
                {
                    "id": "mastery_nodes",
                    "type": "bar",
                    "title": "Mastery path nodes completed",
                    "labels": list(mastery_summary.keys()),
                    "series": [
                        {
                            "name": "completed_nodes",
                            "data": [
                                mastery_summary.get(lbl, {}).get("completed_nodes", 0)
                                for lbl in mastery_summary
                            ],
                        }
                    ],
                },
                {
                    "id": "grammar_radar",
                    "type": "radar",
                    "title": f"Grammar skill balance ({focus_level or 'all'})",
                    "labels": list(grammar_radar.keys()),
                    "series": [{"name": "strength", "data": list(grammar_radar.values())}],
                },
            ],
            "stats": {
                "notebook_entries": notebook_count,
                "levels_with_progress": len(
                    [lvl for lvl, count in words_by_level.items() if count > 0]
                ),
            },
        }

    async def _words_learned_by_level(
        self, db: AsyncSession, *, user_id: uuid.UUID
    ) -> dict[str, int]:
        rows = (
            await db.execute(
                select(Word.level, func.count())
                .join(UserWordProgress, UserWordProgress.word_id == Word.id)
                .where(UserWordProgress.user_id == user_id)
                .group_by(Word.level)
            )
        ).all()
        ordered = [lvl.value for lvl in CEFRLevel]
        counts = {lvl: 0 for lvl in ordered}
        for level, count in rows:
            counts[str(level.value if hasattr(level, "value") else level)] = int(count)
        return counts

    async def _mastery_summary(
        self, db: AsyncSession, *, user_id: uuid.UUID
    ) -> dict[str, dict[str, Any]]:
        rows = (
            await db.execute(
                select(UserMasteryProgress).where(UserMasteryProgress.user_id == user_id)
            )
        ).scalars().all()
        ordered = [lvl.value for lvl in CEFRLevel]
        summary: dict[str, dict[str, Any]] = {lvl: {"completed_nodes": 0} for lvl in ordered}
        for row in rows:
            level = str(row.level.value if hasattr(row.level, "value") else row.level)
            progress = row.progress_json or {}
            nodes = progress.get("nodes") or {}
            completed = sum(
                1
                for node in nodes.values()
                if isinstance(node, dict) and node.get("status") in {"passed", "mastered"}
            )
            summary[level] = {"completed_nodes": completed, "version": row.version}
        return summary

    async def _notebook_count(self, db: AsyncSession, *, user_id: uuid.UUID) -> int:
        result = await db.execute(
            select(func.count())
            .select_from(WordNotebookEntry)
            .where(WordNotebookEntry.user_id == user_id)
        )
        return int(result.scalar_one())

    def _pick_focus_level(
        self,
        mastery_summary: dict[str, dict[str, Any]],
        words_by_level: dict[str, int],
    ) -> str | None:
        for level in reversed(list(words_by_level.keys())):
            if words_by_level.get(level, 0) > 0:
                return level
        for level in reversed(list(mastery_summary.keys())):
            if mastery_summary.get(level, {}).get("completed_nodes", 0) > 0:
                return level
        return "A1"

    def _grammar_radar_from_mastery(
        self,
        mastery_summary: dict[str, dict[str, Any]],
        focus_level: str | None,
    ) -> dict[str, int]:
        base = {
            "word_order": 40,
            "verbs": 40,
            "articles": 40,
            "pronouns": 40,
            "connectors": 40,
        }
        if not focus_level:
            return base
        completed = mastery_summary.get(focus_level, {}).get("completed_nodes", 0)
        boost = min(completed * 8, 50)
        return {skill: min(100, score + boost) for skill, score in base.items()}


_service: VisualizeService | None = None


def get_visualize_service() -> VisualizeService:
    global _service
    if _service is None:
        _service = VisualizeService()
    return _service
