from __future__ import annotations

import json
import random
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.base import CEFRLevel
from backend.app.modules.learning.models import Word
from backend.app.modules.book.models import (
    BlockStatus,
    BlockType,
    LessonBlock,
    LessonBook,
    LessonPage,
    LessonPageOutline,
)
from backend.app.modules.learning.engine import ensure_words_seeded, get_level_definitions
from backend.app.modules.learning.quiz.templates import GLOSS_EN, build_template_quiz
from backend.app.modules.learning.quiz.models import ExerciseType

SPINES_DIR = Path(__file__).resolve().parent / "spines"


def load_book_spine(level: CEFRLevel) -> LessonBook:
    path = SPINES_DIR / f"{level.value.lower()}.json"
    if not path.exists():
        raise FileNotFoundError(f"No lesson book for {level.value}")
    return LessonBook.model_validate(json.loads(path.read_text(encoding="utf-8")))


def find_page_outline(book: LessonBook, page_id: str) -> tuple[str, LessonPageOutline]:
    for chapter in book.chapters:
        for page in chapter.pages:
            if page.id == page_id:
                return chapter.id, page
    raise KeyError(page_id)


class LessonCompiler:
    async def compile_page(
        self,
        db: AsyncSession,
        *,
        level: CEFRLevel,
        page_id: str,
    ) -> LessonPage:
        await ensure_words_seeded(db)
        book = load_book_spine(level)
        chapter_id, outline = find_page_outline(book, page_id)
        words = (
            await db.execute(
                select(Word)
                .where(Word.level == level)
                .where(Word.rank >= outline.word_rank_min)
                .where(Word.rank <= outline.word_rank_max)
                .order_by(Word.rank)
            )
        ).scalars().all()
        if not words:
            words = (
                await db.execute(
                    select(Word).where(Word.level == level).order_by(Word.rank).limit(12)
                )
            ).scalars().all()

        level_meta = next(
            (item for item in get_level_definitions() if item["level"] == level),
            {},
        )
        grammar = outline.grammar_topic or str(level_meta.get("grammar_focus") or "")
        objectives = [
            f"Learn vocabulary ranks {outline.word_rank_min}–{outline.word_rank_max}",
            f"Practice: {grammar}",
        ]

        blocks: list[LessonBlock] = [
            self._text_block(outline, grammar, level.value),
            self._vocabulary_block(words),
            self._dialogue_block(words),
            self._pronunciation_block(words),
            self._listening_block(words),
            await self._quiz_block(db, words, level),
        ]
        return LessonPage(
            id=outline.id,
            book_id=book.id,
            level=level.value,
            chapter_id=chapter_id,
            title=outline.title,
            grammar_topic=grammar,
            learning_objectives=objectives,
            blocks=blocks,
        )

    def _text_block(self, outline: LessonPageOutline, grammar: str, level: str) -> LessonBlock:
        body = (
            f"Welcome to **{outline.title}** ({level}).\n\n"
            f"In this lesson you will meet new Dutch words and practice **{grammar}**.\n\n"
            "Work through each block: vocabulary → dialogue → pronunciation → listening → quiz."
        )
        return LessonBlock(
            id=f"blk_{uuid.uuid4().hex[:8]}",
            type=BlockType.TEXT,
            title="Introduction",
            payload={"markdown": body},
        )

    def _vocabulary_block(self, words: list[Word]) -> LessonBlock:
        sample = words[:8]
        cards = []
        for word in sample:
            gloss = GLOSS_EN.get(word.lemma, "Dutch word")
            cards.append(
                {
                    "front": word.lemma,
                    "back": gloss,
                    "hint": f"rank {word.rank}",
                    "word_id": str(word.id),
                }
            )
        return LessonBlock(
            id=f"blk_{uuid.uuid4().hex[:8]}",
            type=BlockType.VOCABULARY,
            title="Vocabulary",
            payload={"cards": cards},
        )

    def _dialogue_block(self, words: list[Word]) -> LessonBlock:
        lemmas = [word.lemma for word in words[:4]] or ["hallo", "dag"]
        lines = [
            {"speaker": "A", "text": f"Hallo! Ik ben Anna."},
            {"speaker": "B", "text": f"Hallo Anna. Ik ben Tom."},
            {"speaker": "A", "text": f"{' '.join(lemmas[:2])} — dat zijn nieuwe woorden."},
            {"speaker": "B", "text": "Ja, laten we oefenen!"},
        ]
        return LessonBlock(
            id=f"blk_{uuid.uuid4().hex[:8]}",
            type=BlockType.DIALOGUE,
            title="Dialogue",
            payload={
                "scenario": "Two learners meet and practice new words.",
                "lines": lines,
                "practice_prompt": "Read role B's lines aloud, then write your own greeting.",
            },
        )

    def _pronunciation_block(self, words: list[Word]) -> LessonBlock:
        targets = [{"word": word.lemma, "note": "Repeat slowly 3×"} for word in words[:5]]
        return LessonBlock(
            id=f"blk_{uuid.uuid4().hex[:8]}",
            type=BlockType.PRONUNCIATION,
            title="Pronunciation",
            payload={
                "items": targets,
                "tts_placeholder": True,
                "instruction": "Audio/TTS coming soon — read each word aloud for now.",
            },
        )

    def _listening_block(self, words: list[Word]) -> LessonBlock:
        target = random.choice(words) if words else None
        lemma = target.lemma if target else "hallo"
        return LessonBlock(
            id=f"blk_{uuid.uuid4().hex[:8]}",
            type=BlockType.LISTENING,
            title="Listening",
            payload={
                "audio_url": "",
                "transcript": f"Ik zeg {lemma}. Kun je het horen?",
                "comprehension_question": f"Which word did you hear? ({lemma})",
                "expected_answer": lemma,
            },
        )

    async def _quiz_block(self, db: AsyncSession, words: list[Word], level: CEFRLevel) -> LessonBlock:
        questions = build_template_quiz(
            words=words,
            level=level,
            count=min(3, len(words) or 1),
            exercise_types=[ExerciseType.RECOGNITION, ExerciseType.RECALL],
        )
        payload_questions = []
        for question in questions:
            payload_questions.append(
                {
                    "id": question.id,
                    "prompt": question.prompt,
                    "question_type": question.question_type,
                    "options": question.options,
                    "correct_answer": question.correct_answer,
                    "explanation": question.explanation,
                    "word_id": str(question.word_id) if question.word_id else None,
                    "exercise_type": question.exercise_type.value,
                }
            )
        return LessonBlock(
            id=f"blk_{uuid.uuid4().hex[:8]}",
            type=BlockType.QUIZ,
            title="Lesson quiz",
            payload={"questions": payload_questions},
        )


_compiler: LessonCompiler | None = None


def get_lesson_compiler() -> LessonCompiler:
    global _compiler
    if _compiler is None:
        _compiler = LessonCompiler()
    return _compiler
