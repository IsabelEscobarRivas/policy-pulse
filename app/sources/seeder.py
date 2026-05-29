from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.models.regulatory_source import RegulatorySource
from app.sources.registry import SOURCES
from app.storage.database import SessionLocal


def seed_sources(db: Session) -> None:
    for source in SOURCES:
        existing = (
            db.query(RegulatorySource)
            .filter(RegulatorySource.source_name == source["source_name"])
            .first()
        )
        if existing:
            continue

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
