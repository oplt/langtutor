from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.app.modules.learning.models import Word
    from backend.app.modules.users.models import User


class WordNotebookEntry(Base, TimestampMixin):
    __tablename__ = "word_notebook_entries"

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
    word_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("words.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    lemma: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    note: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    context: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    source: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'manual'"))
    session_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    user: Mapped["User"] = relationship(back_populates="notebook_entries")
    word: Mapped[Optional["Word"]] = relationship()

    __table_args__ = (
        UniqueConstraint("user_id", "lemma", name="uq_word_notebook_user_lemma"),
        Index("ix_word_notebook_user_created", "user_id", "created_at"),
    )
