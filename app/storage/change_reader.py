from typing import List

from sqlalchemy.orm import Session

from app.models.regulatory_change import RegulatoryChange


def get_recent_changes(db: Session, limit: int = 20) -> List[RegulatoryChange]:
    return (
        db.query(RegulatoryChange)
        .filter(RegulatoryChange.filtered_out.is_(False))
        .order_by(RegulatoryChange.detected_at.desc())
        .limit(limit)
        .all()
    )


def get_changes_by_source(db: Session, source_id: str) -> List[RegulatoryChange]:
    return (
        db.query(RegulatoryChange)
        .filter(
            RegulatoryChange.source_id == source_id,
            RegulatoryChange.filtered_out.is_(False),
        )
        .order_by(RegulatoryChange.detected_at.desc())
        .all()
    )
