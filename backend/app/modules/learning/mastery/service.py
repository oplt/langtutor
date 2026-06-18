from __future__ import annotations

import json
import random
import time
import uuid
from pathlib import Path

from backend.app.modules.learning.mastery.models import (
    DrillTemplate,
    KnowledgePoint,
    KnowledgeType,
    LearningModule,
    LearningProgress,
    LearningStage,
    PendingQuestion,
    QuizAttempt,
)
from backend.app.modules.learning.mastery.grading import classify_error, grade_answer
from backend.app.modules.learning.mastery.mastery import compute_mastery
from backend.app.modules.learning.mastery.models import ErrorRecord, RetryAttempt
from backend.app.modules.learning.mastery.scheduler import SpacedRepetitionScheduler

PATHS_DIR = Path(__file__).resolve().parent.parent / "paths"


def load_path_definition(level: str) -> list[LearningModule]:
    path_file = PATHS_DIR / f"{level.lower()}.json"
    if not path_file.exists():
        raise FileNotFoundError(f"No mastery path for level {level}")
    payload = json.loads(path_file.read_text(encoding="utf-8"))
    modules: list[LearningModule] = []
    for raw in payload.get("modules", []):
        kps = []
        for kp_raw in raw.get("knowledge_points", []):
            drills = [
                DrillTemplate.model_validate(item) for item in kp_raw.get("drills", [])
            ]
            kps.append(
                KnowledgePoint(
                    id=str(kp_raw["id"]),
                    name=str(kp_raw["name"]),
                    type=KnowledgeType(str(kp_raw["type"])),
                    module_id=str(raw["id"]),
                    rank_min=kp_raw.get("rank_min"),
                    rank_max=kp_raw.get("rank_max"),
                    drills=drills,
                )
            )
        modules.append(
            LearningModule(
                id=str(raw["id"]),
                name=str(raw["name"]),
                order=int(raw.get("order", 0)),
                stage=LearningStage(str(raw.get("stage", "practice"))),
                pass_threshold=float(raw.get("pass_threshold", 0.7)),
                knowledge_points=kps,
            )
        )
    return sorted(modules, key=lambda item: item.order)


class MasteryService:
    def __init__(self, scheduler: SpacedRepetitionScheduler | None = None) -> None:
        self._scheduler = scheduler or SpacedRepetitionScheduler()

    def new_progress(self, path_id: str, modules: list[LearningModule]) -> LearningProgress:
        progress = LearningProgress(path_id=path_id.upper())
        self.replace_modules(progress, modules)
        return progress

    def replace_modules(self, progress: LearningProgress, modules: list[LearningModule]) -> None:
        new_kp_ids = {kp.id for module in modules for kp in module.knowledge_points}
        for key in list(progress.mastery_levels.keys()):
            if key not in new_kp_ids:
                del progress.mastery_levels[key]
        for key in list(progress.knowledge_types.keys()):
            if key not in new_kp_ids:
                del progress.knowledge_types[key]
        for key in list(progress.repetition_states.keys()):
            if key not in new_kp_ids:
                del progress.repetition_states[key]
        progress.error_records = [
            record for record in progress.error_records if record.knowledge_point_id in new_kp_ids
        ]
        progress.review_queue = [
            task for task in progress.review_queue if task.knowledge_point_id in new_kp_ids
        ]
        progress.modules = list(modules)
        for module in modules:
            for kp in module.knowledge_points:
                progress.knowledge_types[kp.id] = kp.type
        progress.updated_at = time.time()

    def calculate_mastery(self, progress: LearningProgress, kp_id: str) -> float:
        correctness = [
            attempt.is_correct
            for attempt in progress.quiz_attempts
            if attempt.knowledge_point_id == kp_id
        ]
        return compute_mastery(correctness)

    def record_quiz_attempt(self, progress: LearningProgress, attempt: QuizAttempt) -> None:
        if not attempt.is_correct and attempt.error_type is not None:
            existing = next(
                (
                    record
                    for record in progress.error_records
                    if record.question_id == attempt.question_id
                    and record.knowledge_point_id == attempt.knowledge_point_id
                ),
                None,
            )
            if existing is not None:
                existing.retry_history.append(
                    RetryAttempt(
                        timestamp=time.time(),
                        is_correct=False,
                        attempt_number=len(existing.retry_history) + 1,
                    )
                )
                existing.status = "retrying"
            else:
                progress.error_records.append(
                    ErrorRecord(
                        id=uuid.uuid4().hex,
                        question_id=attempt.question_id,
                        knowledge_point_id=attempt.knowledge_point_id,
                        module_id=attempt.module_id,
                        error_type=attempt.error_type,
                        status="active",
                    )
                )
        elif attempt.is_correct:
            for record in progress.error_records:
                if (
                    record.question_id == attempt.question_id
                    and record.knowledge_point_id == attempt.knowledge_point_id
                    and record.status in ("active", "retrying")
                ):
                    record.retry_history.append(
                        RetryAttempt(
                            timestamp=time.time(),
                            is_correct=True,
                            attempt_number=len(record.retry_history) + 1,
                        )
                    )
                    record.status = "graduated"
                    break
        progress.quiz_attempts.append(attempt)
        progress.updated_at = time.time()

    def grade_and_record(
        self,
        progress: LearningProgress,
        *,
        question_id: str,
        knowledge_point_id: str,
        module_id: str,
        user_answer: str,
        expected_answer: str,
        question_type: str = "short",
    ) -> bool:
        is_correct = bool(expected_answer) and grade_answer(
            user_answer, expected_answer, question_type
        )
        self.record_quiz_attempt(
            progress,
            QuizAttempt(
                question_id=question_id,
                knowledge_point_id=knowledge_point_id,
                module_id=module_id,
                is_correct=is_correct,
                user_answer=user_answer,
                error_type=None if is_correct else classify_error(user_answer),
            ),
        )
        if knowledge_point_id:
            progress.mastery_levels[knowledge_point_id] = self.calculate_mastery(
                progress, knowledge_point_id
            )
            kp_type = progress.knowledge_types.get(knowledge_point_id)
            if kp_type is not None:
                state = progress.repetition_states.get(
                    knowledge_point_id
                ) or self._scheduler.get_initial_state(kp_type)
                progress.repetition_states[knowledge_point_id] = state
                self._scheduler.schedule_next(state, kp_type, is_correct)
                progress.review_queue = self._scheduler.build_review_queue(progress)
        progress.pending_question = None
        progress.updated_at = time.time()
        return is_correct

    def set_pending_question(self, progress: LearningProgress, pending: PendingQuestion) -> None:
        progress.pending_question = pending
        progress.updated_at = time.time()

    def record_qualitative(
        self,
        progress: LearningProgress,
        kp_id: str,
        *,
        passed: bool,
        evidence: str = "",
    ) -> None:
        progress.qualitative_mastery[kp_id] = bool(passed)
        current = progress.mastery_levels.get(kp_id, 0.0)
        progress.mastery_levels[kp_id] = max(current, 1.0) if passed else min(current, 0.4)
        if evidence:
            progress.feynman_explanations[kp_id] = evidence
        progress.updated_at = time.time()

    def pick_drill(self, kp: KnowledgePoint) -> DrillTemplate | None:
        if kp.drills:
            return random.choice(kp.drills)
        return None

    def build_pending_from_drill(
        self,
        *,
        kp: KnowledgePoint,
        module_id: str,
        drill: DrillTemplate,
    ) -> PendingQuestion:
        return PendingQuestion(
            question_id=uuid.uuid4().hex,
            knowledge_point_id=kp.id,
            module_id=module_id,
            prompt=drill.prompt,
            question_type=drill.question_type,
            expected_answer=drill.expected_answer,
            options=list(drill.options),
        )
