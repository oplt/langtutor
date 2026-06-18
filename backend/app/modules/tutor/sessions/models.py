from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base, TimestampMixin


class TutorChatSession(Base, TimestampMixin):
    __tablename__ = "tutor_chat_sessions"

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
    session_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    capability: Mapped[str] = mapped_column(String(64), nullable=False, server_default=text("'chat'"))
    language: Mapped[str] = mapped_column(String(8), nullable=False, server_default=text("'en'"))
    cefr_level: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    persona: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    last_turn_at: Mapped[Optional[Any]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "session_id", name="uq_tutor_user_session"),
        Index("ix_tutor_sessions_user_last_turn", "user_id", "last_turn_at"),
    )


class TutorChatTurn(Base, TimestampMixin):
    __tablename__ = "tutor_chat_turns"

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
    session_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    turn_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    parent_turn_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    seq: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    status: Mapped[str] = mapped_column(String(24), nullable=False, server_default=text("'running'"))
    capability: Mapped[str] = mapped_column(String(64), nullable=False, server_default=text("'chat'"))
    language: Mapped[str] = mapped_column(String(8), nullable=False, server_default=text("'en'"))
    cefr_level: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    persona: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    user_message: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    conversation_history: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )

    assistant_reply: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    paused: Mapped[bool] = mapped_column(server_default=text("false"), nullable=False)
    pause_question: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Stored for replay/debugging. (May grow; prune later if needed.)
    events: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )

    __table_args__ = (
        Index("ix_tutor_turns_session_created", "session_id", "created_at"),
    )

