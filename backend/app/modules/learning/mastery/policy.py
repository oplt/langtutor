from __future__ import annotations

from dataclasses import dataclass
import time

from backend.app.modules.learning.mastery.models import (
    KnowledgePoint,
    KnowledgeType,
    LearningProgress,
    ReviewTask,
)

QUANTITATIVE_GATE: dict[KnowledgeType, float] = {
    KnowledgeType.MEMORY: 0.9,
    KnowledgeType.PROCEDURE: 0.9,
}

QUALITATIVE_TYPES: frozenset[KnowledgeType] = frozenset(
    {KnowledgeType.CONCEPT, KnowledgeType.DESIGN}
)

_QUALITATIVE_PASS_DISPLAY = 1.0


def gate_threshold(kp_type: KnowledgeType) -> float:
    if kp_type in QUALITATIVE_TYPES:
        return _QUALITATIVE_PASS_DISPLAY
    return QUANTITATIVE_GATE.get(kp_type, 0.9)


def is_mastered(progress: LearningProgress, kp: KnowledgePoint) -> bool:
    if kp.type in QUALITATIVE_TYPES:
        return bool(progress.qualitative_mastery.get(kp.id, False))
    return progress.mastery_levels.get(kp.id, 0.0) >= gate_threshold(kp.type)


def display_mastery(progress: LearningProgress, kp: KnowledgePoint) -> float:
    if kp.type in QUALITATIVE_TYPES and progress.qualitative_mastery.get(kp.id):
        return _QUALITATIVE_PASS_DISPLAY
    return float(progress.mastery_levels.get(kp.id, 0.0))


def objective_status(progress: LearningProgress, kp: KnowledgePoint) -> str:
    if is_mastered(progress, kp):
        return "mastered"
    seen = any(a.knowledge_point_id == kp.id for a in progress.quiz_attempts) or (
        kp.id in progress.qualitative_mastery
    )
    return "learning" if seen else "new"


def due_reviews(progress: LearningProgress, *, now: float | None = None) -> list[ReviewTask]:
    moment = time.time() if now is None else now
    due = [task for task in progress.review_queue if task.due_at <= moment]
    due.sort(key=lambda task: task.priority)
    return due


@dataclass(frozen=True)
class NextStep:
    action: str
    module_id: str = ""
    module_name: str = ""
    knowledge_point_id: str = ""
    knowledge_point_name: str = ""
    knowledge_point_type: str = ""
    stage: str = ""
    status: str = ""
    gate: str = ""
    mastery: float = 0.0
    threshold: float = 0.0
    reason: str = ""
    pending_prompt: str = ""

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "module_id": self.module_id,
            "module_name": self.module_name,
            "knowledge_point_id": self.knowledge_point_id,
            "knowledge_point_name": self.knowledge_point_name,
            "knowledge_point_type": self.knowledge_point_type,
            "stage": self.stage,
            "status": self.status,
            "gate": self.gate,
            "mastery": round(self.mastery, 3),
            "threshold": round(self.threshold, 3),
            "reason": self.reason,
            "pending_prompt": self.pending_prompt,
        }


def find_knowledge_point(
    progress: LearningProgress, kp_id: str
) -> tuple[KnowledgePoint | None, str, str, str]:
    for module in progress.modules:
        for kp in module.knowledge_points:
            if kp.id == kp_id:
                return kp, module.id, module.name, module.stage.value
    return None, "", "", ""


def _gate_kind(kp: KnowledgePoint) -> str:
    return "qualitative" if kp.type in QUALITATIVE_TYPES else "quantitative"


def next_objective(progress: LearningProgress, *, now: float | None = None) -> NextStep:
    pending = progress.pending_question
    if pending is not None:
        kp, module_id, module_name, stage = find_knowledge_point(
            progress, pending.knowledge_point_id
        )
        return NextStep(
            action="answer_pending",
            module_id=module_id or pending.module_id,
            module_name=module_name,
            knowledge_point_id=pending.knowledge_point_id,
            knowledge_point_name=kp.name if kp else "",
            knowledge_point_type=kp.type.value if kp else "",
            stage=stage,
            status=objective_status(progress, kp) if kp else "learning",
            gate=_gate_kind(kp) if kp else "",
            mastery=display_mastery(progress, kp) if kp else 0.0,
            threshold=gate_threshold(kp.type) if kp else 0.0,
            reason="Answer the pending question before continuing.",
            pending_prompt=pending.prompt,
        )

    due = due_reviews(progress, now=now)
    if due:
        kp, module_id, module_name, stage = find_knowledge_point(
            progress, due[0].knowledge_point_id
        )
        if kp is not None:
            return NextStep(
                action="review",
                module_id=module_id,
                module_name=module_name,
                knowledge_point_id=kp.id,
                knowledge_point_name=kp.name,
                knowledge_point_type=kp.type.value,
                stage=stage,
                status=objective_status(progress, kp),
                gate=_gate_kind(kp),
                mastery=display_mastery(progress, kp),
                threshold=gate_threshold(kp.type),
                reason="Spaced review is due for this objective.",
            )

    for module in sorted(progress.modules, key=lambda item: item.order):
        for kp in module.knowledge_points:
            if is_mastered(progress, kp):
                continue
            status = objective_status(progress, kp)
            gate = _gate_kind(kp)
            if status == "new":
                action = "probe"
            elif gate == "qualitative":
                action = "assess"
            else:
                action = "practice"
            return NextStep(
                action=action,
                module_id=module.id,
                module_name=module.name,
                knowledge_point_id=kp.id,
                knowledge_point_name=kp.name,
                knowledge_point_type=kp.type.value,
                stage=module.stage.value,
                status=status,
                gate=gate,
                mastery=display_mastery(progress, kp),
                threshold=gate_threshold(kp.type),
                reason=(
                    "Probe this new objective before teaching."
                    if status == "new"
                    else "Keep working until the mastery gate clears."
                ),
            )

    return NextStep(action="complete", reason="All objectives mastered and no reviews due.")


def map_summary(progress: LearningProgress, *, now: float | None = None) -> dict:
    counts = {"mastered": 0, "learning": 0, "new": 0, "total": 0}
    modules_out: list[dict] = []
    for module in sorted(progress.modules, key=lambda item: item.order):
        kps_out: list[dict] = []
        mastered = 0
        for kp in module.knowledge_points:
            status = objective_status(progress, kp)
            counts[status] += 1
            counts["total"] += 1
            if status == "mastered":
                mastered += 1
            kps_out.append(
                {
                    "id": kp.id,
                    "name": kp.name,
                    "type": kp.type.value,
                    "status": status,
                    "mastery": round(display_mastery(progress, kp), 3),
                }
            )
        modules_out.append(
            {
                "id": module.id,
                "name": module.name,
                "order": module.order,
                "stage": module.stage.value,
                "mastered": mastered,
                "total": len(module.knowledge_points),
                "knowledge_points": kps_out,
            }
        )
    return {
        "counts": counts,
        "due_reviews": len(due_reviews(progress, now=now)),
        "complete": counts["total"] > 0 and counts["mastered"] == counts["total"],
        "modules": modules_out,
    }


def level_gate_complete(progress: LearningProgress) -> bool:
    summary = map_summary(progress)
    return bool(summary["complete"])
