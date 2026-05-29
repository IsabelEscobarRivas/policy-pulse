import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class RegulatoryDocument(Base):
    __tablename__ = "regulatory_documents"
    __table_args__ = (
        UniqueConstraint("content_hash", name="uq_regulatory_documents_content_hash"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    source_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("regulatory_sources.id"), nullable=False
    )
    external_url: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
