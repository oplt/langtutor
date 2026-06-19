from __future__ import annotations

import json
import logging
import re
import uuid

from backend.app.db.base import CEFRLevel
from backend.app.modules.learning.mastery.grading import grade_answer
from backend.app.modules.learning.quiz.models import ExerciseType, QuizQuestion
from backend.app.modules.llm.base import LLMMessage
from backend.app.modules.llm.service import get_llm_service
from backend.app.modules.prompt.assembler import build_task_system_prompt

logger = logging.getLogger(__name__)

_JUDGE_SYSTEM = {
    "en": (
        "You grade Dutch language learner answers. Be rigorous but encouraging.\n"
        "First line: ✅ Correct / ⚠️ Partially correct / ❌ Incorrect — brief reason.\n"
        "Then bullets: what worked, what to fix. Reply in English."
    ),
    "nl": (
        "Je beoordeelt antwoorden van Nederlandse taalleerders. Wees streng maar bemoedigend.\n"
        "Eerste regel: ✅ Correct / ⚠️ Gedeeltelijk correct / ❌ Incorrect — korte reden.\n"
        "Daarna bullets. Antwoord in het Nederlands."
    ),
}


def _parse_llm_questions(raw: str, words: list) -> list[QuizQuestion]:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    else:
        start = text.find("[")
        end = text.rfind("]")
        if start >= 0 and end > start:
            text = text[start : end + 1]
    payload = json.loads(text)
    if not isinstance(payload, list):
        return []
    word_by_lemma = {word.lemma.lower(): word for word in words}
    questions: list[QuizQuestion] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        lemma = str(item.get("lemma") or item.get("word") or "").strip().lower()
        word = word_by_lemma.get(lemma)
        exercise_raw = str(item.get("exercise_type") or "recall").lower()
        try:
            exercise = ExerciseType(exercise_raw)
        except ValueError:
            exercise = ExerciseType.RECALL
        qtype = str(item.get("question_type") or "short")
        options_raw = item.get("options") or []
        options = (
            [str(opt) for opt in options_raw]
            if isinstance(options_raw, list)
            else list(options_raw.values())
            if isinstance(options_raw, dict)
            else []
        )
        questions.append(
            QuizQuestion(
                id=str(uuid.uuid4()),
                word_id=word.id if word else None,
                lemma=lemma,
                exercise_type=exercise,
                question_type=qtype,
                prompt=str(item.get("prompt") or item.get("question") or ""),
                options=options,
                correct_answer=str(item.get("correct_answer") or item.get("answer") or ""),
                explanation=str(item.get("explanation") or ""),
                use_ai_judge=bool(item.get("use_ai_judge") or qtype == "open"),
            )
        )
    return [question for question in questions if question.prompt and question.correct_answer]


async def generate_llm_quiz(
    *,
    level: CEFRLevel,
    words: list,
    count: int,
    exercise_types: list[ExerciseType],
    topic: str = "",
) -> list[QuizQuestion]:
    lemmas = [word.lemma for word in words[:40]]
    type_names = ", ".join(exercise.value for exercise in exercise_types)
    system = build_task_system_prompt(task="quiz_generation", ui_language="en", cefr_level=level.value)
    user = (
        f"Generate {count} Dutch exercises for CEFR {level.value}.\n"
        f"Exercise types to use: {type_names}.\n"
        f"Topic focus: {topic or 'general vocabulary'}.\n"
        f"Target words (use these lemmas): {', '.join(lemmas[:20])}.\n\n"
        "Return ONLY a JSON array. Each item:\n"
        '{"lemma":"...","exercise_type":"recognition|recall|production|fill_blank|translation",'
        '"question_type":"choice|short|open","prompt":"...","options":["..."],"correct_answer":"...",'
        '"explanation":"...","use_ai_judge":false}\n'
        "For recognition include 4 options. For production use question_type open and use_ai_judge true."
    )
    try:
        response = await get_llm_service().complete(
            "quiz_generation",
            [
                LLMMessage(role="system", content=system),
                LLMMessage(role="user", content=user),
            ],
            temperature=0.3,
            max_tokens=2048,
        )
        parsed = _parse_llm_questions(response.content, words)
        return parsed[:count]
    except Exception as exc:
        logger.exception("LLM quiz generation failed")
        raise QuizGenerationError("llm_quiz_generation_failed") from exc


class QuizGenerationError(RuntimeError):
    """LLM quiz generation failed; callers may fall back to templates."""


async def judge_with_llm(
    *,
    prompt: str,
    question_type: str,
    correct_answer: str,
    explanation: str,
    user_answer: str,
    options: list[str] | None = None,
    language: str = "en",
) -> dict:
    trimmed = user_answer.strip()
    if question_type in {"choice", "short", "fill_blank"} and trimmed:
        qtype = "choice" if question_type == "choice" else "short"
        if grade_answer(trimmed, correct_answer, qtype):
            return {
                "verdict": "correct",
                "correct": True,
                "feedback": "Correct!",
            }

    lang = "nl" if language.lower().startswith("nl") else "en"
    system = _JUDGE_SYSTEM[lang]
    options_block = "\n".join(f"- {opt}" for opt in (options or []))
    user = (
        f"Question type: {question_type}\n"
        f"Prompt: {prompt}\n"
        f"Options:\n{options_block or '(none)'}\n"
        f"Reference answer: {correct_answer}\n"
        f"Explanation: {explanation or '(none)'}\n"
        f"Learner answer: {user_answer}\n"
    )
    text = ""
    async for chunk in get_llm_service().stream(
        "correction",
        [
            LLMMessage(role="system", content=system),
            LLMMessage(role="user", content=user),
        ],
        temperature=0.2,
        max_tokens=512,
    ):
        text += chunk
    verdict = _verdict_from_text(text)
    return {
        "verdict": verdict,
        "correct": verdict in {"correct", "partial"},
        "feedback": text.strip(),
    }


def _verdict_from_text(text: str) -> str:
    lowered = text.lower()
    if "❌" in text or "incorrect" in lowered:
        return "incorrect"
    if "⚠️" in text or "partial" in lowered or "gedeeltelijk" in lowered:
        return "partial"
    if "✅" in text or "correct" in lowered:
        return "correct"
    return "incorrect"


def grade_deterministic(
    *,
    question_type: str,
    correct_answer: str,
    user_answer: str,
) -> bool:
    return grade_answer(user_answer, correct_answer, question_type)
