from backend.app.modules.learning.mastery.models import (
    ErrorRecord,
    ErrorType,
    KnowledgeType,
    LearningProgress,
    RepetitionState,
)
from backend.app.modules.learning.mastery.scheduler import SpacedRepetitionScheduler


def test_schedule_next_advances_on_correct_answers() -> None:
    scheduler = SpacedRepetitionScheduler()
    state = scheduler.get_initial_state(KnowledgeType.MEMORY)
    first_interval = scheduler.interval_days_for_index(KnowledgeType.MEMORY, 0)

    state = scheduler.schedule_next(state, KnowledgeType.MEMORY, is_correct=True)
    assert state.interval_index >= 1
    assert state.consecutive_wrong == 0
    assert state.next_review_at > 0
    assert first_interval == 0


def test_schedule_next_steps_back_on_wrong_answers() -> None:
    scheduler = SpacedRepetitionScheduler()
    state = RepetitionState(
        interval_index=3,
        consecutive_correct=0,
        consecutive_wrong=0,
        next_review_at=0.0,
    )
    state = scheduler.schedule_next(state, KnowledgeType.MEMORY, is_correct=False)
    assert state.interval_index <= 3
    assert state.consecutive_correct == 0


def test_build_review_queue_prioritizes_error_knowledge_points() -> None:
    scheduler = SpacedRepetitionScheduler()
    progress = LearningProgress(
        path_id="a1",
        knowledge_types={"kp1": KnowledgeType.MEMORY, "kp2": KnowledgeType.MEMORY},
        repetition_states={
            "kp1": RepetitionState(interval_index=1, consecutive_correct=0, consecutive_wrong=0, next_review_at=1.0),
            "kp2": RepetitionState(interval_index=1, consecutive_correct=0, consecutive_wrong=0, next_review_at=2.0),
        },
        error_records=[
            ErrorRecord(
                id="err1",
                question_id="q1",
                knowledge_point_id="kp2",
                module_id="m1",
                error_type=ErrorType.APPLICATION_ERROR,
                status="active",
            )
        ],
    )
    tasks = scheduler.build_review_queue(progress)
    assert tasks
    by_id = {task.knowledge_point_id: task for task in tasks}
    assert by_id["kp2"].priority < by_id["kp1"].priority
