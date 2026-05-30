import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class Interpretation(Base):
    __tablename__ = "interpretations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    change_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("regulatory_changes.id"), nullable=False
    )
    source_name: Mapped[str] = mapped_column(String, nullable=False)
    interpreted_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    visa_category: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    change_type_label: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_implications: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review_priority: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    raw_llm_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    governance_flagged: Mapped[bool] = mapped_column(Boolean, default=False)
