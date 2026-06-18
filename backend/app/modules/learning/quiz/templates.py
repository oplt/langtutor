from __future__ import annotations

import random
import uuid
from typing import Iterable

from backend.app.db.base import CEFRLevel
from backend.app.modules.learning.quiz.models import ExerciseType, QuizQuestion

# Minimal gloss hints for template translation/recall prompts (expand over time).
GLOSS_EN: dict[str, str] = {
    "hallo": "hello",
    "dag": "goodbye / day",
    "dank": "thanks",
    "ja": "yes",
    "nee": "no",
    "ik": "I",
    "jij": "you",
    "hij": "he",
    "zij": "she / they",
    "wij": "we",
    "huis": "house",
    "water": "water",
    "brood": "bread",
    "moeder": "mother",
    "vader": "father",
    "kind": "child",
    "goed": "good",
    "groot": "big",
    "klein": "small",
    "nieuw": "new",
    "oud": "old",
}

SENTENCE_FRAMES = [
    "Ik zie {w}.",
    "Dat is {w}.",
    "Wij gebruiken {w}.",
    "Hier is {w}.",
]


def _distractors(words: list, target, count: int = 3) -> list[str]:
    pool = [word.lemma for word in words if word.id != target.id and word.lemma != target.lemma]
    random.shuffle(pool)
    return pool[:count]


def build_recognition(word, words: list) -> QuizQuestion:
    options = [word.lemma, *_distractors(words, word)]
    random.shuffle(options)
    gloss = GLOSS_EN.get(word.lemma, word.lemma)
    return QuizQuestion(
        id=str(uuid.uuid4()),
        word_id=word.id,
        lemma=word.lemma,
        exercise_type=ExerciseType.RECOGNITION,
        question_type="choice",
        prompt=f"Which Dutch word means '{gloss}'?",
        options=options,
        correct_answer=word.lemma,
        explanation=f"'{word.lemma}' = {gloss}",
    )


def build_recall(word) -> QuizQuestion:
    gloss = GLOSS_EN.get(word.lemma, "this word")
    return QuizQuestion(
        id=str(uuid.uuid4()),
        word_id=word.id,
        lemma=word.lemma,
        exercise_type=ExerciseType.RECALL,
        question_type="short",
        prompt=f"Type the Dutch word for '{gloss}'.",
        correct_answer=word.lemma,
        explanation=f"The Dutch word is '{word.lemma}'.",
    )


def build_fill_blank(word) -> QuizQuestion:
    frame = random.choice(SENTENCE_FRAMES).format(w="___")
    return QuizQuestion(
        id=str(uuid.uuid4()),
        word_id=word.id,
        lemma=word.lemma,
        exercise_type=ExerciseType.FILL_BLANK,
        question_type="short",
        prompt=f"Fill in the blank: {frame}",
        correct_answer=word.lemma,
        explanation=f"Correct word: {word.lemma}",
    )


def build_translation(word, *, to_dutch: bool = True) -> QuizQuestion:
    gloss = GLOSS_EN.get(word.lemma, word.lemma)
    if to_dutch:
        prompt = f"Translate to Dutch: {gloss}"
        answer = word.lemma
    else:
        prompt = f"Translate to English: {word.lemma}"
        answer = gloss
    return QuizQuestion(
        id=str(uuid.uuid4()),
        word_id=word.id,
        lemma=word.lemma,
        exercise_type=ExerciseType.TRANSLATION,
        question_type="short",
        prompt=prompt,
        correct_answer=answer,
        explanation=f"{word.lemma} ↔ {gloss}",
    )


def build_production(word) -> QuizQuestion:
    gloss = GLOSS_EN.get(word.lemma, word.lemma)
    return QuizQuestion(
        id=str(uuid.uuid4()),
        word_id=word.id,
        lemma=word.lemma,
        exercise_type=ExerciseType.PRODUCTION,
        question_type="open",
        prompt=(
            f"Write one short Dutch sentence using the word '{word.lemma}' "
            f"({gloss})."
        ),
        correct_answer=word.lemma,
        explanation="Your sentence should use the target word naturally.",
        use_ai_judge=True,
    )


BUILDERS = {
    ExerciseType.RECOGNITION: lambda w, words: build_recognition(w, words),
    ExerciseType.RECALL: lambda w, words: build_recall(w),
    ExerciseType.FILL_BLANK: lambda w, words: build_fill_blank(w),
    ExerciseType.TRANSLATION: lambda w, words: build_translation(w),
    ExerciseType.PRODUCTION: lambda w, words: build_production(w),
}


def build_template_quiz(
    *,
    words: Iterable,
    level: CEFRLevel,
    count: int,
    exercise_types: list[ExerciseType],
) -> list[QuizQuestion]:
    word_list = list(words)
    if not word_list:
        return []
    random.shuffle(word_list)
    selected = word_list[: max(count, 1)]
    questions: list[QuizQuestion] = []
    for index, word in enumerate(selected):
        exercise = exercise_types[index % len(exercise_types)]
        builder = BUILDERS[exercise]
        questions.append(builder(word, word_list))
    return questions
