import json

from sqlalchemy.orm import Session

from app.models.interpretation import Interpretation
from app.models.regulatory_change import RegulatoryChange
from app.models.regulatory_source import RegulatorySource


def save_interpretation(
    db: Session,
    change: RegulatoryChange,
    interpretation: dict,
    raw_response: str,
    flagged: bool,
) -> Interpretation:
    source = (
        db.query(RegulatorySource)
        .filter(RegulatorySource.id == change.source_id)
        .first()
    )
    source_name = source.source_name if source else "Unknown"

    record = Interpretation(
        change_id=change.id,
        source_name=source_name,
        visa_category=interpretation.get("visa_category"),
        change_type_label=interpretation.get("change_type_label"),
        summary=interpretation.get("summary"),
        evidence_implications=json.dumps(
            interpretation.get("evidence_implications", [])
        ),
        review_priority=interpretation.get("review_priority"),
        raw_llm_response=raw_response,
        governance_flagged=flagged,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
