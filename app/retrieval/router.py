import logging
import time

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.detection.engine import (
    compare_snapshots,
    filter_relevance,
    summarize_delta,
)
from app.models.regulatory_document import RegulatoryDocument
from app.models.regulatory_source import RegulatorySource
from app.normalization.extractor import (
    compute_hash,
    normalize_api_response,
    normalize_html_response,
    normalize_rss_response,
)
from app.retrieval.bright_data_client import BrightDataClient, get_bright_data_client
from app.sources.registry import SOURCES
from app.storage.change_reader import get_recent_changes
from app.storage.change_writer import save_change
from app.storage.database import get_db
from app.storage.writer import save_document

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/retrieve", tags=["retrieval"])


@router.get("/sources")
async def list_sources(db: Session = Depends(get_db)):
    sources = db.query(RegulatorySource).filter(RegulatorySource.active.is_(True)).all()
    return [
        {
            "id": source.id,
            "source_name": source.source_name,
            "source_type": source.source_type,
            "base_url": source.base_url,
            "retrieval_method": source.retrieval_method,
        }
        for source in sources
    ]


@router.get("/documents")
async def list_documents(db: Session = Depends(get_db)):
    documents = (
        db.query(RegulatoryDocument)
        .order_by(RegulatoryDocument.retrieved_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": document.id,
            "source_id": document.source_id,
            "external_url": document.external_url,
            "title": document.title,
            "content_hash": document.content_hash,
            "retrieved_at": str(document.retrieved_at),
        }
        for document in documents
    ]


@router.get("/changes")
async def list_changes(db: Session = Depends(get_db)):
    changes = get_recent_changes(db, limit=20)
    return [
        {
            "id": change.id,
            "source_id": change.source_id,
            "detected_at": str(change.detected_at),
            "change_type": change.change_type,
            "relevance_score": change.relevance_score,
            "delta_summary": change.delta_summary,
            "filtered_out": change.filtered_out,
        }
        for change in changes
    ]


@router.post("/debug/{source_type}")
async def debug_retrieve(
    source_type: str,
    client: BrightDataClient = Depends(get_bright_data_client),
):
    source_registry = {
        "newsroom": "https://www.uscis.gov/newsroom",
        "policy_manual": "https://www.uscis.gov/policy-manual",
        "visa_bulletin": "https://travel.state.gov/content/travel/en/legal/visa-law0/visa-bulletin.html",
    }
    url = source_registry.get(source_type)
    if not url:
        raise HTTPException(status_code=404, detail="Source not found")

    response = await client.fetch_serp(url)
    return response


@router.post("/{source_type}")
async def retrieve_source(
    source_type: str,
    db: Session = Depends(get_db),
    client: BrightDataClient = Depends(get_bright_data_client),
):
    source = (
        db.query(RegulatorySource)
        .filter(
            RegulatorySource.source_type == source_type,
            RegulatorySource.active.is_(True),
        )
        .first()
    )
    if not source:
        raise HTTPException(status_code=404, detail="Source not found or inactive")

    start = time.monotonic()

    try:
        if source.retrieval_method == "api":
            response = await client.fetch_api(source.base_url)
            normalized = normalize_api_response(response, source.base_url)
        elif source.retrieval_method == "rss":
            xml = await client.fetch_rss(source.base_url)
            normalized = normalize_rss_response(xml, source.base_url)
        elif source.retrieval_method == "html":
            html = await client.fetch_html(source.base_url)
            normalized = normalize_html_response(html, source.base_url)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown retrieval method: {source.retrieval_method}",
            )

        current_document, created = save_document(db, source.id, normalized)
        content_hash = compute_hash(normalized["body"])
        content_size = len(normalized["body"])
        elapsed = time.monotonic() - start

        previous_document = (
            db.query(RegulatoryDocument)
            .filter(RegulatoryDocument.source_id == source.id)
            .order_by(RegulatoryDocument.retrieved_at.desc())
            .offset(1)
            .limit(1)
            .first()
        )

        if previous_document is None:
            change = save_change(
                db,
                source.id,
                current_document,
                None,
                {"added": [], "removed": [], "change_detected": False},
                0.0,
                "First retrieval — no previous snapshot.",
            )
        else:
            delta = compare_snapshots(
                previous_document.content or "",
                current_document.content or "",
            )
            filtered_delta, relevance_score = filter_relevance(delta)
            summary = summarize_delta(filtered_delta, source.source_name)
            change = save_change(
                db,
                source.id,
                current_document,
                previous_document,
                filtered_delta,
                relevance_score,
                summary,
            )

        logger.info(
            "retrieval complete source_type=%s url=%s content_size=%s hash=%s created=%s time=%.2fs",
            source_type,
            source.base_url,
            content_size,
            content_hash,
            created,
            elapsed,
        )

        return {
            "source_type": source_type,
            "url": source.base_url,
            "title": normalized["title"],
            "content_size": content_size,
            "content_hash": content_hash,
            "created": created,
            "retrieved_at": normalized["timestamp"],
            "change_type": change.change_type,
            "relevance_score": change.relevance_score,
            "delta_summary": change.delta_summary,
        }
    except httpx.HTTPStatusError as e:
        logger.error(f"Bright Data request failed: {e}")
        raise HTTPException(
            status_code=502, detail=f"Upstream retrieval failed: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error during retrieval of {source_type}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
