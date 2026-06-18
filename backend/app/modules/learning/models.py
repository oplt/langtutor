from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Enum as SAEnum

from backend.app.db.base import Base, CEFRLevel, TimestampMixin


class Word(Base, TimestampMixin):
    __tablename__ = "words"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        unique=True,
        nullable=False,
    )
    lemma: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    rank: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    level: Mapped[CEFRLevel] = mapped_column(SAEnum(CEFRLevel, name="cefr_level"), nullable=False, index=True)

    forms: Mapped[List["WordForm"]] = relationship(
        back_populates="word",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    stories: Mapped[List["StoryWord"]] = relationship(
        back_populates="word",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    user_progress: Mapped[List["UserWordProgress"]] = relationship(
        back_populates="word",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_words_level_rank", "level", "rank"),
    )


class WordForm(Base, TimestampMixin):
    __tablename__ = "word_forms"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        unique=True,
        nullable=False,
    )
    word_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("words.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    form: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    features: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    word: Mapped["Word"] = relationship(back_populates="forms")


class UserWordProgress(Base, TimestampMixin):
    __tablename__ = "user_word_progress"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        unique=True,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    word_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("words.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recognition_strength: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    recall_strength: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    production_strength: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    ease_factor: Mapped[float] = mapped_column(Float, nullable=False, server_default=text("2.5"))
    interval_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_review_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="word_progress")
    word: Mapped["Word"] = relationship(back_populates="user_progress")

    __table_args__ = (
        UniqueConstraint("user_id", "word_id", name="uq_user_word_progress"),
        Index("ix_user_word_progress_review", "user_id", "next_review_at"),
    )


class UserLessonPageProgress(Base, TimestampMixin):
    __tablename__ = "user_lesson_page_progress"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        unique=True,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    level: Mapped[CEFRLevel] = mapped_column(SAEnum(CEFRLevel, name="cefr_level"), nullable=False, index=True)
    page_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    quiz_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped["User"] = relationship(back_populates="lesson_page_progress")

    __table_args__ = (
        UniqueConstraint("user_id", "page_id", name="uq_user_lesson_page"),
    )


class UserMasteryProgress(Base, TimestampMixin):
    __tablename__ = "user_mastery_progress"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        unique=True,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    level: Mapped[CEFRLevel] = mapped_column(SAEnum(CEFRLevel, name="cefr_level"), nullable=False, index=True)
    progress_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

    user: Mapped["User"] = relationship(back_populates="mastery_progress")

    __table_args__ = (
        UniqueConstraint("user_id", "level", name="uq_user_mastery_level"),
    )
