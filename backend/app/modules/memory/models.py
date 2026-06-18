from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Enum as SAEnum

from backend.app.db.base import Base, TimestampMixin

MEMORY_SURFACES = ("chat", "quiz", "story", "practice", "tutor")
L3_SLOTS = ("recent", "profile", "scope", "preferences")


class UserMemoryTrace(Base, TimestampMixin):
    __tablename__ = "user_memory_traces"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    surface: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    turn_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    payload: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    user: Mapped["User"] = relationship(back_populates="memory_traces")

    __table_args__ = (
        Index("ix_user_memory_traces_user_surface", "user_id", "surface"),
    )


class UserMemoryDocument(Base, TimestampMixin):
    __tablename__ = "user_memory_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    layer: Mapped[str] = mapped_column(String(8), nullable=False)
    doc_key: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    entries: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

    user: Mapped["User"] = relationship(back_populates="memory_documents")

    __table_args__ = (
        UniqueConstraint("user_id", "layer", "doc_key", name="uq_user_memory_doc"),
        Index("ix_user_memory_documents_lookup", "user_id", "layer", "doc_key"),
    )
