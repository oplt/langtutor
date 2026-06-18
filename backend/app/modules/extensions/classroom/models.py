from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base, CEFRLevel, TimestampMixin
from sqlalchemy.types import Enum as SAEnum


class ClassroomGrant(Base, TimestampMixin):
    """Teacher ↔ student classroom link without exposing API keys."""

    __tablename__ = "classroom_grants"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        nullable=False,
    )
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assigned_level: Mapped[CEFRLevel | None] = mapped_column(
        SAEnum(CEFRLevel, name="cefr_level"),
        nullable=True,
    )
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        UniqueConstraint("teacher_id", "student_id", name="uq_classroom_teacher_student"),
    )
