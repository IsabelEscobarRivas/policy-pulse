import json
from typing import Optional

from sqlalchemy.orm import Session

from app.models.regulatory_change import RegulatoryChange
from app.models.regulatory_document import RegulatoryDocument


def save_change(
    db: Session,
    source_id: str,
    current_document: RegulatoryDocument,
    previous_document: Optional[RegulatoryDocument],
    delta: dict,
    relevance_score: float,
    summary: str,
) -> RegulatoryChange:
    if previous_document is None:
        change_type = "new_document"
    elif not delta.get("change_detected", False):
        change_type = "no_change"
    else:
        change_type = "content_modified"

    change = RegulatoryChange(
        source_id=source_id,
        change_type=change_type,
        previous_hash=previous_document.content_hash if previous_document else None,
        current_hash=current_document.content_hash,
        delta_summary=summary,
        added_sentences=json.dumps(delta.get("added", [])),
        removed_sentences=json.dumps(delta.get("removed", [])),
        relevance_score=relevance_score,
        filtered_out=relevance_score == 0.0,
    )
    db.add(change)
    db.commit()
    db.refresh(change)
    return change
