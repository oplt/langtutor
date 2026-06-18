from __future__ import annotations

import asyncio
import json
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from sqlalchemy import func, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.base import CEFRLevel
from backend.app.modules.learning.models import UserWordProgress, Word
from backend.app.modules.learning.mastery.models import KnowledgeType, RepetitionState
from backend.app.modules.learning.mastery.scheduler import SpacedRepetitionScheduler
from backend.app.modules.stories.models import Story, StoryWord
from backend.app.core.config import BASE_DIR


LEVEL_DEFINITIONS: List[Dict[str, object]] = [
    {
        "level": CEFRLevel.A1,
        "rank_min": 1,
        "rank_max": 200,
        "word_coverage": "Top 200 words",
        "grammar_focus": "Simple present, basic sentences",
        "input_type": "Micro-stories",
    },
    {
        "level": CEFRLevel.A2,
        "rank_min": 201,
        "rank_max": 500,
        "word_coverage": "Top 500 words",
        "grammar_focus": "Past tense, modal verbs",
        "input_type": "Short narratives",
    },
    {
        "level": CEFRLevel.B1,
        "rank_min": 501,
        "rank_max": 1000,
        "word_coverage": "Top 1000 words",
        "grammar_focus": "Subordinate clauses",
        "input_type": "Dialogues",
    },
    {
        "level": CEFRLevel.B2,
        "rank_min": 1001,
        "rank_max": 2000,
        "word_coverage": "Top 2000 words",
        "grammar_focus": "Relative clauses",
        "input_type": "Real-life scenarios",
    },
    {
        "level": CEFRLevel.C1,
        "rank_min": 2001,
        "rank_max": 3000,
        "word_coverage": "Top 3000 words",
        "grammar_focus": "Idiomatic structures",
        "input_type": "News-style texts",
    },
    {
        "level": CEFRLevel.C2,
        "rank_min": 3001,
        "rank_max": 4000,
        "word_coverage": "4000+ words",
        "grammar_focus": "Natural discourse",
        "input_type": "Authentic-like content",
    },
]

LEVEL_ORDER = [CEFRLevel.A1, CEFRLevel.A2, CEFRLevel.B1, CEFRLevel.B2, CEFRLevel.C1, CEFRLevel.C2]

STOPWORDS = {
    "de", "het", "een", "en", "ik", "jij", "je", "hij", "zij", "we", "wij", "jullie", "u",
    "is", "ben", "zijn", "was", "waren", "heb", "hebt", "heeft", "hebben",
    "ga", "gaat", "gaan", "naar", "in", "op", "niet", "maar", "met", "voor", "van",
    "dat", "dit", "die", "er", "hier", "daar", "als", "om", "te",
}

TITLES = {
    CEFRLevel.A1: ["Een kleine dag", "Thuis en buiten", "Samen vandaag"],
    CEFRLevel.A2: ["Een korte reis", "Een nieuw plan", "In de stad"],
    CEFRLevel.B1: ["Een goed gesprek", "Het nieuwe werk", "De volgende stap"],
    CEFRLevel.B2: ["Een moeilijke keuze", "Een echte situatie", "De lange middag"],
    CEFRLevel.C1: ["Een onverwacht nieuws", "Een scherpe discussie", "Het volgende hoofdstuk"],
    CEFRLevel.C2: ["Het volledige verhaal", "Een complex moment", "De grote lijn"],
}

TEMPLATES = {
    CEFRLevel.A1: [
        "Ik zie {w}.",
        "Jij ziet {w}.",
        "Wij gaan naar {w}.",
        "Daar is {w}.",
        "Het is goed.",
        "Wij praten over {w}.",
        "Ik zeg: dank je.",
        "Tot morgen.",
    ],
    CEFRLevel.A2: [
        "Ik zag {w} in de stad.",
        "Jij ging naar {w}.",
        "We spraken over {w}.",
        "Later kwam {w} terug.",
        "Het was een rustige avond.",
        "We maakten een plan met {w}.",
        "We bleven nog even daar.",
        "Tot de volgende dag.",
    ],
    CEFRLevel.B1: [
        "Ik denk aan {w} terwijl ik loop.",
        "Jij zegt dat {w} belangrijk is.",
        "We gaan verder, omdat {w} helpt.",
        "In het gesprek komt {w} terug.",
        "Het verhaal groeit en wordt duidelijk.",
        "We kiezen een richting met {w}.",
        "De tijd gaat snel voorbij.",
        "We sluiten af met een korte vraag.",
    ],
    CEFRLevel.B2: [
        "Ik merkte dat {w} onverwacht veranderde.",
        "Jij vertelde waarom {w} nodig was.",
        "We bespraken {w}, hoewel het lastig bleef.",
        "Het gesprek maakte de situatie duidelijk.",
        "Daarna besloten we om door te gaan.",
        "We hielden rekening met {w}.",
        "De keuze werd uiteindelijk gemaakt.",
        "We keken terug op het resultaat.",
    ],
    CEFRLevel.C1: [
        "Ik stelde vast dat {w} meer impact had dan gedacht.",
        "Jij legde uit hoe {w} ons plan veranderde.",
        "We onderzochten {w} en trokken conclusies.",
        "Het verhaal kreeg een nieuwe betekenis.",
        "We vergeleken verschillende opties.",
        "De discussie bleef scherp en inhoudelijk.",
        "Uiteindelijk werd de richting helder.",
        "We gingen verder met een nieuw inzicht.",
    ],
    CEFRLevel.C2: [
        "Ik analyseerde {w} en zag de bredere context.",
        "Jij verbond {w} met eerdere beslissingen.",
        "We nuanceerden {w} en verfijnden onze argumenten.",
        "Het gesprek ontwikkelde zich tot een volledige analyse.",
        "We wegen de gevolgen zorgvuldig af.",
        "De conclusie bleef stevig onderbouwd.",
        "Daarna vertaalden we de ideeën naar actie.",
        "We sloten af met een helder perspectief.",
    ],
}


def level_for_rank(rank: int) -> CEFRLevel:
    for definition in LEVEL_DEFINITIONS:
        if definition["rank_min"] <= rank <= definition["rank_max"]:
            return definition["level"]  # type: ignore[return-value]
    return CEFRLevel.C2


def get_level_definitions() -> List[Dict[str, object]]:
    return [definition.copy() for definition in LEVEL_DEFINITIONS]


def _normalize_word(value: str) -> str:
    return value.strip().lower()


def _pick_title(level: CEFRLevel) -> str:
    options = TITLES.get(level) or ["Kort verhaal"]
    return random.choice(options)


def _compose_story(level: CEFRLevel, target_words: List[str], new_words: List[str], max_words: int) -> str:
    slot_words = [w for w in target_words if _normalize_word(w) not in STOPWORDS and len(w) >= 3]
    if not slot_words:
        slot_words = target_words[:]

    templates = TEMPLATES.get(level, TEMPLATES[CEFRLevel.A1])
    sentences: List[str] = []
    for idx in range(max(len(slot_words), len(templates))):
        template = templates[idx % len(templates)]
        word = slot_words[idx % len(slot_words)]
        sentences.append(template.format(w=word))

    if new_words:
        sentences.append(f"Nieuwe woorden: {', '.join(new_words)}.")
    sentences.append("Herhaal de zinnen hardop en maak je eigen variant.")

    body = " ".join(sentences)
    words = body.split()
    if len(words) > max_words:
        body = " ".join(words[:max_words]).rstrip(".") + "."
    return body


async def ensure_words_seeded(db: AsyncSession) -> int:
    existing = await db.execute(select(func.count(Word.id)))
    count = existing.scalar_one() or 0
    if count > 0:
        return 0

    path = BASE_DIR / "files" / "dutchwordsordered.json"
    payload = await asyncio.to_thread(json.loads, path.read_text(encoding="utf-8"))
    items = payload.get("words", [])
    rows = []
    for item in items:
        word = _normalize_word(str(item.get("word", "")))
        if not word:
            continue
        rank = int(item.get("rank", 0))
        if rank <= 0:
            continue
        rows.append({
            "lemma": word,
            "rank": rank,
            "level": level_for_rank(rank),
        })

    if not rows:
        return 0

    try:
        await db.execute(insert(Word), rows)
        await db.flush()
        from backend.app.modules.learning.response_cache import invalidate_levels_cache

        await invalidate_levels_cache()
        return len(rows)
    except IntegrityError:
        # Another request likely seeded in parallel.
        await db.rollback()
        return 0


async def level_counts(db: AsyncSession) -> Dict[CEFRLevel, int]:
    result = await db.execute(
        select(Word.level, func.count(Word.id)).group_by(Word.level)
    )
    rows = result.all()
    counts: Dict[CEFRLevel, int] = {level: 0 for level in LEVEL_ORDER}
    for level, count in rows:
        counts[level] = count
    return counts


def _pick_diverse_words(words: List[Word], count: int) -> List[Word]:
    if count <= 0:
        return []
    if len(words) <= count:
        return random.sample(words, len(words))
    ordered = sorted(words, key=lambda item: item.rank)
    step = max(1, len(ordered) // count)
    picked: List[Word] = []
    for index in range(count):
        candidate = ordered[min(index * step, len(ordered) - 1)]
        if candidate not in picked:
            picked.append(candidate)
    if len(picked) < count:
        remaining = [word for word in ordered if word not in picked]
        random.shuffle(remaining)
        picked.extend(remaining[: count - len(picked)])
    return picked[:count]


async def pick_story_words(
    db: AsyncSession,
    level: CEFRLevel,
    target_word_count: int,
) -> Tuple[List[Word], List[Word]]:
    current_words = (
        await db.execute(
            select(Word).where(Word.level == level).order_by(Word.rank)
        )
    ).scalars().all()

    if level == CEFRLevel.A1:
        new_count = target_word_count
        review_count = 0
    else:
        new_count = max(1, round(target_word_count * 0.3))
        review_count = max(0, target_word_count - new_count)

    new_words = _pick_diverse_words(list(current_words), new_count)

    if review_count <= 0:
        return new_words, []

    current_index = LEVEL_ORDER.index(level)
    prior_levels = LEVEL_ORDER[:current_index]
    review_candidates: List[Word] = []
    if prior_levels:
        review_candidates = (
            await db.execute(
                select(Word).where(Word.level.in_(prior_levels)).order_by(Word.rank)
            )
        ).scalars().all()
        random.shuffle(review_candidates)

    review_words = review_candidates[:review_count]
    if len(review_words) < review_count:
        remaining = review_count - len(review_words)
        extra = [w for w in current_words if w not in new_words][:remaining]
        review_words.extend(extra)

    return new_words, review_words


@dataclass
class StoryPackage:
    story: Story
    new_words: List[Word]
    review_words: List[Word]


async def generate_story(
    db: AsyncSession,
    level: CEFRLevel,
    target_word_count: int = 10,
    max_words: int = 180,
) -> StoryPackage:
    await ensure_words_seeded(db)
    new_words, review_words = await pick_story_words(db, level, target_word_count)
    target_words = new_words + review_words

    title = _pick_title(level)
    body = _compose_story(
        level,
        [w.lemma for w in target_words],
        [w.lemma for w in new_words],
        max_words,
    )

    story = Story(
        level=level,
        title=title,
        body=body,
        word_count=len(body.split()),
        new_word_count=len(new_words),
        metadata_json={
            "target_words": [w.lemma for w in target_words],
            "new_words": [w.lemma for w in new_words],
        },
    )
    db.add(story)
    await db.flush()

    for index, word in enumerate(target_words):
        db.add(
            StoryWord(
                story_id=story.id,
                word_id=word.id,
                is_new=word in new_words,
                position=index,
            )
        )
    await db.flush()
    return StoryPackage(story=story, new_words=new_words, review_words=review_words)


_srs = SpacedRepetitionScheduler()


async def update_word_progress(
    db: AsyncSession,
    user_id,
    word_id,
    event: str,
    correct: bool,
) -> UserWordProgress:
    existing = (
        await db.execute(
            select(UserWordProgress)
            .where(UserWordProgress.user_id == user_id)
            .where(UserWordProgress.word_id == word_id)
        )
    ).scalar_one_or_none()

    if existing is None:
        existing = UserWordProgress(user_id=user_id, word_id=word_id)
        db.add(existing)

    delta = 10 if correct else -6
    if event == "recognition":
        existing.recognition_strength = max(0, min(100, existing.recognition_strength + delta))
    elif event == "recall":
        existing.recall_strength = max(0, min(100, existing.recall_strength + delta))
    elif event == "production":
        existing.production_strength = max(0, min(100, existing.production_strength + delta))

    kp_type = KnowledgeType.MEMORY
    if existing.interval_days:
        state = RepetitionState(
            interval_index=max(0, min(existing.interval_days, 6)),
            consecutive_correct=0,
            consecutive_wrong=0,
            next_review_at=(
                existing.next_review_at.timestamp()
                if existing.next_review_at
                else time.time()
            ),
        )
    else:
        state = _srs.get_initial_state(kp_type)
    _srs.schedule_next(state, kp_type, correct)
    existing.interval_days = _srs.interval_days_for_index(kp_type, state.interval_index)
    existing.ease_factor = min(2.8, existing.ease_factor + 0.05) if correct else max(
        1.3, existing.ease_factor - 0.1
    )

    existing.last_seen_at = datetime.now(timezone.utc)
    existing.next_review_at = datetime.fromtimestamp(state.next_review_at, tz=timezone.utc)
    await db.flush()
    return existing
