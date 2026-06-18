from __future__ import annotations

import random
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.base import CEFRLevel
from backend.app.modules.learning.engine import ensure_words_seeded
from backend.app.modules.learning.mastery.models import DrillTemplate, KnowledgePoint, PendingQuestion
from backend.app.modules.learning.mastery.policy import find_knowledge_point, next_objective
from backend.app.modules.learning.mastery.repository import MasteryRepository
from backend.app.modules.learning.mastery.service import MasteryService, load_path_definition
from backend.app.modules.learning.models import Word


class MasteryPathRuntime:
    def __init__(self) -> None:
        self._service = MasteryService()
        self._repo = MasteryRepository()

    async def ensure_path(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        level: CEFRLevel,
    ):
        modules = load_path_definition(level.value)

        def factory():
            return self._service.new_progress(level.value, modules)

        return await self._repo.get_or_create(
            db, user_id=user_id, level=level, factory=factory
        )

    async def get_map(self, db: AsyncSession, *, user_id: uuid.UUID, level: CEFRLevel) -> dict:
        from backend.app.modules.learning.mastery.policy import map_summary

        row, progress = await self.ensure_path(db, user_id=user_id, level=level)
        return {
            "level": level.value,
            "next": next_objective(progress).to_dict(),
            "map": map_summary(progress),
            "version": row.version,
        }

    async def get_next(self, db: AsyncSession, *, user_id: uuid.UUID, level: CEFRLevel) -> dict:
        _, progress = await self.ensure_path(db, user_id=user_id, level=level)
        return next_objective(progress).to_dict()

    async def register_quiz(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        level: CEFRLevel,
        knowledge_point_id: str,
        prompt: str,
        expected_answer: str,
        question_type: str = "short",
        options: list[str] | None = None,
    ) -> dict:
        row, progress = await self.ensure_path(db, user_id=user_id, level=level)
        kp, module_id, _, _ = find_knowledge_point(progress, knowledge_point_id)
        if kp is None:
            raise ValueError("knowledge_point_not_found")
        pending = PendingQuestion(
            question_id=str(uuid.uuid4()),
            knowledge_point_id=knowledge_point_id,
            module_id=module_id,
            prompt=prompt,
            expected_answer=expected_answer,
            question_type=question_type,
            options=options or [],
        )
        self._service.set_pending_question(progress, pending)
        await self._repo.save(db, row, progress)
        return pending.model_dump()

    async def grade_answer(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        level: CEFRLevel,
        user_answer: str,
    ) -> dict:
        from backend.app.modules.learning.mastery.policy import map_summary

        row, progress = await self.ensure_path(db, user_id=user_id, level=level)
        pending = progress.pending_question
        if pending is None:
            raise ValueError("no_pending_question")
        is_correct = self._service.grade_and_record(
            progress,
            question_id=pending.question_id,
            knowledge_point_id=pending.knowledge_point_id,
            module_id=pending.module_id,
            user_answer=user_answer,
            expected_answer=pending.expected_answer,
            question_type=pending.question_type,
        )
        await self._repo.save(db, row, progress)
        await ensure_words_seeded(db)
        drill = await self._build_drill_from_progress(
            db,
            level=level,
            row=row,
            progress=progress,
        )
        return {
            "correct": is_correct,
            "map": {
                "level": level.value,
                "next": next_objective(progress).to_dict(),
                "map": map_summary(progress),
                "version": row.version,
            },
            "drill": drill,
        }

    async def assess_qualitative(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        level: CEFRLevel,
        knowledge_point_id: str,
        passed: bool,
        evidence: str = "",
    ) -> dict:
        row, progress = await self.ensure_path(db, user_id=user_id, level=level)
        self._service.record_qualitative(
            progress, knowledge_point_id, passed=passed, evidence=evidence
        )
        await self._repo.save(db, row, progress)
        return {"passed": passed, "next": next_objective(progress).to_dict()}

    async def build_drill(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        level: CEFRLevel,
    ) -> dict:
        await ensure_words_seeded(db)
        row, progress = await self.ensure_path(db, user_id=user_id, level=level)
        return await self._build_drill_from_progress(
            db,
            level=level,
            row=row,
            progress=progress,
        )

    async def _build_drill_from_progress(
        self,
        db: AsyncSession,
        *,
        level: CEFRLevel,
        row,
        progress,
    ) -> dict:
        step = next_objective(progress)
        if step.action in {"complete", "answer_pending"}:
            return {"step": step.to_dict(), "drill": None}

        kp, module_id, _, _ = find_knowledge_point(progress, step.knowledge_point_id)
        if kp is None:
            return {"step": step.to_dict(), "drill": None}

        drill = self._service.pick_drill(kp)
        if drill is None and kp.rank_min and kp.rank_max:
            drill = await self._word_drill(db, level=level, kp=kp)
        if drill is None:
            return {"step": step.to_dict(), "drill": None}

        pending = self._service.build_pending_from_drill(
            kp=kp, module_id=module_id, drill=drill
        )
        self._service.set_pending_question(progress, pending)
        await self._repo.save(db, row, progress)
        return {
            "step": step.to_dict(),
            "drill": {
                "question_id": pending.question_id,
                "knowledge_point_id": pending.knowledge_point_id,
                "prompt": pending.prompt,
                "question_type": pending.question_type,
                "options": pending.options,
            },
        }

    async def _word_drill(
        self,
        db: AsyncSession,
        *,
        level: CEFRLevel,
        kp: KnowledgePoint,
    ) -> DrillTemplate | None:
        words = (
            await db.execute(
                select(Word)
                .where(Word.level == level)
                .where(Word.rank >= (kp.rank_min or 1))
                .where(Word.rank <= (kp.rank_max or 9999))
                .order_by(Word.rank)
            )
        ).scalars().all()
        if not words:
            return None
        target = random.choice(words)
        distractors = random.sample(
            [word.lemma for word in words if word.id != target.id],
            k=min(3, max(0, len(words) - 1)),
        )
        options = [target.lemma, *distractors]
        random.shuffle(options)
        return DrillTemplate(
            prompt=f"Type the Dutch word (from your {level.value} word list):",
            expected_answer=target.lemma,
            question_type="short",
            options=options,
        )


_runtime: MasteryPathRuntime | None = None


def get_mastery_runtime() -> MasteryPathRuntime:
    global _runtime
    if _runtime is None:
        _runtime = MasteryPathRuntime()
    return _runtime
