from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

try:
    from backend.app.db.base_class import Base
except Exception:  # pragma: no cover - adjust to your repo's Base location if needed.
    from backend.app.db.base import Base  # type: ignore


class GeneratedReading(Base):
    """Persistent saved reading record.

    Add an Alembic migration before enabling this in production. If your app
    uses a different Base/model convention, adapt the Base import above.
    """

    __tablename__ = "generated_readings"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    language: Mapped[str] = mapped_column(String(8), default="nl", nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    max_frequency_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    interest_area: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_word_count: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_word_count: Mapped[int] = mapped_column(Integer, nullable=False)
    source_title: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    source_url: Mapped[str] = mapped_column(Text, default="", nullable=False)
    source_publisher: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    source_published_at: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    adapted_text: Mapped[str] = mapped_column(Text, nullable=False)
    translated_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    coverage_percent: Mapped[float] = mapped_column(Float, nullable=False)
    unknown_words: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
