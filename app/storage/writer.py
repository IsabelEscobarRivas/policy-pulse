from typing import Tuple

from sqlalchemy.orm import Session

from app.models.regulatory_document import RegulatoryDocument
from app.models.retrieval_snapshot import RetrievalSnapshot
from app.normalization.extractor import compute_hash


def save_document(
    db: Session, source_id: str, normalized: dict
) -> Tuple[RegulatoryDocument, bool]:
    content_hash = compute_hash(normalized["body"])

    document = RegulatoryDocument(
        source_id=source_id,
        external_url=normalized["source_url"],
        title=normalized["title"] or None,
        content=normalized["body"],
        content_hash=content_hash,
        raw_html=None,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    snapshot = RetrievalSnapshot(
        document_id=document.id,
        normalized_content=normalized["body"],
        content_hash=content_hash,
    )
    db.add(snapshot)
    db.commit()

    return document, True
