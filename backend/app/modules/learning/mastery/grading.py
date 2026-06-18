from __future__ import annotations

import re
from difflib import SequenceMatcher

from backend.app.modules.learning.mastery.models import ErrorType


def grade_answer(user_answer: str, expected_answer: str, question_type: str = "short") -> bool:
    user = user_answer.strip().lower()
    expected = expected_answer.strip().lower()
    if not expected:
        return False
    if question_type == "choice":
        return user.replace(" ", "") == expected.replace(" ", "")
    if question_type == "short":
        if user == expected:
            return True
        if len(expected) <= 30:
            return SequenceMatcher(None, user, expected).ratio() >= 0.85
        return False
    if question_type == "open":
        keywords = [k.strip() for k in re.split(r"[,;.\n]+", expected) if k.strip()]
        if not keywords:
            return False
        matched = sum(1 for kw in keywords if kw in user)
        return matched / len(keywords) >= 0.6
    return False


def classify_error(user_answer: str) -> ErrorType:
    return ErrorType.METACOGNITIVE if not user_answer.strip() else ErrorType.APPLICATION_ERROR
