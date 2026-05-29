import logging

from fastapi import FastAPI

from app.retrieval.router import router as retrieval_router
from app.sources.seeder import register_startup_handlers

logger = logging.getLogger(__name__)

app = FastAPI(title="PolicyPulse", version="0.1.0")

register_startup_handlers(app)


@app.on_event("startup")
def log_startup() -> None:
    logger.info("PolicyPulse started — retrieval endpoints ready")


app.include_router(retrieval_router)


@app.get("/")
def health_check():
    return {"status": "ok", "service": "PolicyPulse"}
