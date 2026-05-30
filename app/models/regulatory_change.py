import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class RegulatoryChange(Base):
    __tablename__ = "regulatory_changes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    source_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("regulatory_sources.id"), nullable=False
    )
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    change_type: Mapped[str] = mapped_column(String, nullable=False)
    previous_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    current_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    delta_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    added_sentences: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    removed_sentences: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    relevance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    filtered_out: Mapped[bool] = mapped_column(Boolean, default=False)
