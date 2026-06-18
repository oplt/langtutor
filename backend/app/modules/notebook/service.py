from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.modules.learning.engine import ensure_words_seeded, update_word_progress
from backend.app.modules.learning.models import UserWordProgress, Word
from backend.app.modules.learning.quiz.templates import GLOSS_EN
from backend.app.modules.notebook.models import WordNotebookEntry


def normalize_lemma(lemma: str) -> str:
    return " ".join(lemma.strip().lower().split())


class NotebookService:
    async def _lookup_word(self, db: AsyncSession, lemma: str) -> Word | None:
        normalized = normalize_lemma(lemma)
        return (
            await db.execute(select(Word).where(func.lower(Word.lemma) == normalized))
        ).scalar_one_or_none()

    async def save_entry(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        lemma: str,
        note: str = "",
        context: str = "",
        source: str = "manual",
        session_id: str | None = None,
        metadata: dict | None = None,
    ) -> WordNotebookEntry:
        await ensure_words_seeded(db)
        normalized = normalize_lemma(lemma)
        if not normalized:
            raise ValueError("lemma_required")

        word = await self._lookup_word(db, normalized)
        row = (
            await db.execute(
                select(WordNotebookEntry)
                .where(WordNotebookEntry.user_id == user_id)
                .where(WordNotebookEntry.lemma == normalized)
            )
        ).scalar_one_or_none()

        if row is None:
            row = WordNotebookEntry(
                user_id=user_id,
                lemma=normalized,
                word_id=word.id if word else None,
                note=note.strip(),
                context=context.strip(),
                source=source,
                session_id=session_id,
                metadata_json=metadata or {},
            )
            db.add(row)
        else:
            if note.strip():
                row.note = note.strip()
            if context.strip():
                row.context = context.strip()
            row.source = source or row.source
            if word and row.word_id is None:
                row.word_id = word.id
            if session_id:
                row.session_id = session_id
            if metadata:
                row.metadata_json = {**(row.metadata_json or {}), **metadata}

        await db.flush()

        if row.word_id:
            progress = (
                await db.execute(
                    select(UserWordProgress)
                    .where(UserWordProgress.user_id == user_id)
                    .where(UserWordProgress.word_id == row.word_id)
                )
            ).scalar_one_or_none()
            if progress is None:
                await update_word_progress(
                    db,
                    user_id=user_id,
                    word_id=row.word_id,
                    event="recognition",
                    correct=False,
                )
            elif progress.next_review_at is None or progress.next_review_at > datetime.now(
                timezone.utc
            ):
                progress.next_review_at = datetime.now(timezone.utc)
                await db.flush()

        return row

    async def list_entries(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
    ) -> list[dict]:
        await ensure_words_seeded(db)
        rows = (
            await db.execute(
                select(WordNotebookEntry, Word, UserWordProgress)
                .outerjoin(Word, Word.id == WordNotebookEntry.word_id)
                .outerjoin(
                    UserWordProgress,
                    (UserWordProgress.word_id == WordNotebookEntry.word_id)
                    & (UserWordProgress.user_id == user_id),
                )
                .where(WordNotebookEntry.user_id == user_id)
                .order_by(WordNotebookEntry.updated_at.desc())
            )
        ).all()

        out: list[dict] = []
        now = datetime.now(timezone.utc)
        for entry, word, progress in rows:
            translation = GLOSS_EN.get(entry.lemma)
            out.append(
                {
                    "id": str(entry.id),
                    "lemma": entry.lemma,
                    "note": entry.note,
                    "context": entry.context,
                    "source": entry.source,
                    "word_id": str(entry.word_id) if entry.word_id else None,
                    "rank": word.rank if word else None,
                    "level": word.level.value if word else None,
                    "translation": translation,
                    "recognition_strength": progress.recognition_strength if progress else None,
                    "recall_strength": progress.recall_strength if progress else None,
                    "next_review_at": progress.next_review_at if progress else None,
                    "created_at": entry.created_at,
                    "updated_at": entry.updated_at,
                    "due": bool(
                        progress
                        and progress.next_review_at
                        and progress.next_review_at <= now
                    ),
                }
            )
        return out

    async def delete_entry(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        entry_id: uuid.UUID,
    ) -> bool:
        row = (
            await db.execute(
                select(WordNotebookEntry)
                .where(WordNotebookEntry.user_id == user_id)
                .where(WordNotebookEntry.id == entry_id)
            )
        ).scalar_one_or_none()
        if row is None:
            return False
        await db.delete(row)
        return True

    async def due_count(self, db: AsyncSession, *, user_id: uuid.UUID) -> int:
        now = datetime.now(timezone.utc)
        entries = await self.list_entries(db, user_id=user_id)
        return sum(1 for item in entries if item.get("due"))


_service: NotebookService | None = None


def get_notebook_service() -> NotebookService:
    global _service
    if _service is None:
        _service = NotebookService()
    return _service
