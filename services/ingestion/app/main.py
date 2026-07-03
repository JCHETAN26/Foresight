"""Ingestion service entrypoint — FastAPI app with lifespan-managed Kafka."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import __version__
from app.kafka_producer import producer
from app.logging import configure_logging, get_logger
from app.webhooks.stripe import router as stripe_router

configure_logging()
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Start/stop the shared Kafka producer with the app lifecycle."""
    await producer.start()
    log.info("ingestion_service_ready", version=__version__)
    try:
        yield
    finally:
        await producer.stop()


app = FastAPI(
    title="Foresight Ingestion",
    version=__version__,
    lifespan=lifespan,
)

app.include_router(stripe_router)


@app.get("/health", tags=["ops"])
async def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok", "version": __version__}
