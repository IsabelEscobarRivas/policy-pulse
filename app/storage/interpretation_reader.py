from typing import List

from sqlalchemy.orm import Session

from app.models.interpretation import Interpretation


def get_recent_interpretations(db: Session, limit: int = 20) -> List[Interpretation]:
    return (
        db.query(Interpretation)
        .order_by(Interpretation.interpreted_at.desc())
        .limit(limit)
        .all()
    )
