"""Structured payload for the ``ask_user`` tool (pause-for-user drills)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

MAX_QUESTIONS = 4
MAX_OPTIONS = 8
MAX_OPTION_CHARS = 120
MAX_OPTION_DESC_CHARS = 200
MAX_HEADER_CHARS = 16
MAX_QUESTION_CHARS = 800
MAX_INTRO_CHARS = 400
MAX_PLACEHOLDER_CHARS = 120

_REDUNDANT_OTHER_LABELS = frozenset({"other", "anders", "iets anders"})


@dataclass(frozen=True)
class AskUserOption:
    label: str
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"label": self.label, "description": self.description}


@dataclass(frozen=True)
class AskUserQuestion:
    id: str
    prompt: str
    options: tuple[AskUserOption, ...] = ()
    header: str | None = None
    multi_select: bool = False
    allow_free_text: bool = True
    placeholder: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "prompt": self.prompt,
            "header": self.header,
            "multi_select": self.multi_select,
            "options": [option.to_dict() for option in self.options],
            "allow_free_text": self.allow_free_text,
            "placeholder": self.placeholder,
        }


@dataclass(frozen=True)
class AskUserPayload:
    questions: tuple[AskUserQuestion, ...]
    intro: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "intro": self.intro,
            "questions": [question.to_dict() for question in self.questions],
        }

    @property
    def primary_prompt(self) -> str:
        if not self.questions:
            return ""
        return self.questions[0].prompt


def build_ask_user_payload(
    *,
    questions: Any = None,
    intro: Any = None,
    question: Any = None,
    options: Any = None,
) -> tuple[AskUserPayload | None, str | None]:
    raw_questions = _coerce_questions(questions, question, options)
    if isinstance(raw_questions, str):
        return None, raw_questions
    if not raw_questions:
        return None, "`questions` must contain at least one question."
    if len(raw_questions) > MAX_QUESTIONS:
        raw_questions = raw_questions[:MAX_QUESTIONS]

    normalised: list[AskUserQuestion] = []
    used_ids: set[str] = set()
    for idx, raw in enumerate(raw_questions):
        built = _build_question(raw, idx, used_ids)
        if isinstance(built, str):
            return None, built
        normalised.append(built)
        used_ids.add(built.id)

    intro_text: str | None = None
    if intro is not None:
        intro_text = _coerce_string(intro).strip() or None
        if intro_text and len(intro_text) > MAX_INTRO_CHARS:
            intro_text = intro_text[:MAX_INTRO_CHARS].rstrip() + "…"

    return AskUserPayload(questions=tuple(normalised), intro=intro_text), None


def format_ask_user_tool_result(
    *,
    reply: str,
    answers: list[dict[str, str]] | None = None,
    payload: AskUserPayload | None = None,
) -> str:
    """Format learner input as tool-result text for loop resume."""
    if answers:
        lines: list[str] = []
        by_id = {question.id: question for question in payload.questions} if payload else {}
        for entry in answers:
            qid = str(entry.get("questionId") or entry.get("id") or "").strip()
            text = str(entry.get("text") or "").strip()
            if not text:
                continue
            label = by_id[qid].prompt if qid in by_id else qid or "answer"
            lines.append(f"{label}: {text}")
        if lines:
            return "Learner answered:\n" + "\n".join(lines)
    cleaned = reply.strip()
    if cleaned:
        return f"Learner answered: {cleaned}"
    return "Learner did not provide an answer."


def _coerce_questions(questions: Any, question: Any, options: Any) -> list[Any] | str:
    if questions is not None:
        if not isinstance(questions, (list, tuple)):
            return "`questions` must be an array."
        return list(questions)
    if question is not None:
        return [{"prompt": question, "options": options}]
    return []


def _build_question(raw: Any, idx: int, used_ids: set[str]) -> AskUserQuestion | str:
    if not isinstance(raw, dict):
        return f"Question #{idx + 1} must be an object."

    prompt_raw = raw.get("prompt")
    if prompt_raw is None:
        prompt_raw = raw.get("question")
    prompt = _coerce_string(prompt_raw).strip()
    if not prompt:
        return f"Question #{idx + 1}: `prompt` must be a non-empty string."
    if len(prompt) > MAX_QUESTION_CHARS:
        prompt = prompt[:MAX_QUESTION_CHARS].rstrip() + "…"

    allow_free_text = raw.get("allow_free_text")
    allow_free_text = True if allow_free_text is None else bool(allow_free_text)

    options_raw = raw.get("options")
    options: tuple[AskUserOption, ...] = ()
    if options_raw is not None:
        if not isinstance(options_raw, (list, tuple)):
            return f"Question #{idx + 1}: `options` must be an array."
        cleaned: list[AskUserOption] = []
        seen_labels: set[str] = set()
        for opt in options_raw:
            normalised = _build_option(opt)
            if normalised is None:
                continue
            if allow_free_text and normalised.label.lower() in _REDUNDANT_OTHER_LABELS:
                continue
            if normalised.label in seen_labels:
                continue
            seen_labels.add(normalised.label)
            cleaned.append(normalised)
            if len(cleaned) >= MAX_OPTIONS:
                break
        options = tuple(cleaned)

    multi_select_raw = raw.get("multi_select")
    if multi_select_raw is None:
        multi_select_raw = raw.get("multiSelect")
    multi_select = bool(multi_select_raw)

    header_raw = raw.get("header")
    header: str | None = None
    if header_raw is not None:
        header = _coerce_string(header_raw).strip() or None
        if header and len(header) > MAX_HEADER_CHARS:
            header = header[:MAX_HEADER_CHARS].rstrip()

    placeholder_raw = raw.get("placeholder")
    placeholder: str | None = None
    if placeholder_raw is not None:
        placeholder = _coerce_string(placeholder_raw).strip() or None
        if placeholder and len(placeholder) > MAX_PLACEHOLDER_CHARS:
            placeholder = placeholder[:MAX_PLACEHOLDER_CHARS].rstrip() + "…"

    qid = _coerce_string(raw.get("id")).strip()
    if not qid:
        qid = f"q{idx + 1}"
    if qid in used_ids:
        suffix = 2
        while f"{qid}_{suffix}" in used_ids:
            suffix += 1
        qid = f"{qid}_{suffix}"

    return AskUserQuestion(
        id=qid,
        prompt=prompt,
        options=options,
        header=header,
        multi_select=multi_select,
        allow_free_text=allow_free_text,
        placeholder=placeholder,
    )


def _build_option(raw: Any) -> AskUserOption | None:
    if isinstance(raw, dict):
        label = _coerce_string(raw.get("label")).strip()
        description = _coerce_string(raw.get("description")).strip() or None
    else:
        label = _coerce_string(raw).strip()
        description = None
    if not label:
        return None
    if len(label) > MAX_OPTION_CHARS:
        label = label[:MAX_OPTION_CHARS].rstrip() + "…"
    if description and len(description) > MAX_OPTION_DESC_CHARS:
        description = description[:MAX_OPTION_DESC_CHARS].rstrip() + "…"
    return AskUserOption(label=label, description=description)


def _coerce_string(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)
