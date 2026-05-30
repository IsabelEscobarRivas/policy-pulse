from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.models import RegulatoryChange
from app.models.regulatory_document import RegulatoryDocument
from app.models.regulatory_source import RegulatorySource
from app.models.retrieval_snapshot import RetrievalSnapshot
from app.sources.registry import SOURCES
from app.storage.database import SessionLocal


def seed_sources(db: Session) -> None:
    db.query(RegulatoryChange).delete()
    db.query(RetrievalSnapshot).delete()
    db.query(RegulatoryDocument).delete()
    db.query(RegulatorySource).delete()
    db.commit()

    for source in SOURCES:
        db.add(
            RegulatorySource(
                source_name=source["source_name"],
                source_type=source["source_type"],
                base_url=source["base_url"],
                retrieval_method=source["retrieval_method"],
                active=source["active"],
            )
        )
    db.commit()


def register_startup_handlers(app: FastAPI) -> None:
    @app.on_event("startup")
    def seed_sources_on_startup() -> None:
        db = SessionLocal()
        try:
            seed_sources(db)
        finally:
            db.close()
