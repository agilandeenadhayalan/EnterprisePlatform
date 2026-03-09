"""
Kafka Consumer Payments — FastAPI application.

Archives payment events to MinIO Bronze AND writes to ClickHouse fact_payments (dual write).

ROUTES:
  POST /process          — Process payment events (dual write: MinIO + ClickHouse)
  GET  /process/stats    — Processing statistics
  GET  /health           — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, Query

# Add project root for mobility-common imports
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app

import config as service_config
import schemas
import repository

# Module-level repository instance
_repo = repository.PaymentProcessorRepository(
    bucket=service_config.settings.archive_bucket,
    prefix=service_config.settings.archive_prefix,
)


def get_repo() -> repository.PaymentProcessorRepository:
    """Dependency — returns the payment processor repository."""
    return _repo


@asynccontextmanager
async def lifespan(app):
    """Startup: initialize ClickHouse + MinIO clients. Shutdown: cleanup."""
    app.state.repo = _repo
    yield


app = create_app(
    title="Kafka Consumer Payments",
    version="0.1.0",
    description="Archives payment events to MinIO Bronze AND writes to ClickHouse fact_payments",
    lifespan=lifespan,
)


# -- Routes --


@app.post("/process", response_model=schemas.ProcessBatchResponse)
async def process_batch(
    body: schemas.ProcessBatchRequest,
    repo: repository.PaymentProcessorRepository = Depends(get_repo),
):
    """Process payment events with dual write: MinIO archive + ClickHouse fact table."""
    results, failed = repo.process_batch(body.events)
    return schemas.ProcessBatchResponse(
        processed=len(results),
        failed=failed,
        clickhouse_written=len(results),
        minio_archived=len(results),
        results=[
            schemas.ProcessedPaymentResponse(
                payment_id=r.payment_id,
                ride_id=r.ride_id,
                amount=r.amount,
                tip_amount=r.tip_amount,
                total_amount=r.total_amount,
                payment_method=r.payment_method,
                status=r.status,
                processed_at=r.processed_at.isoformat(),
            )
            for r in results
        ],
    )


@app.get("/process/stats", response_model=schemas.ProcessingStatsResponse)
async def get_stats(
    repo: repository.PaymentProcessorRepository = Depends(get_repo),
):
    """Return dual-write processing statistics."""
    stats = repo.get_stats()
    return schemas.ProcessingStatsResponse(
        events_processed=stats.events_processed,
        events_failed=stats.events_failed,
        clickhouse_writes=stats.clickhouse_writes,
        minio_writes=stats.minio_writes,
        total_amount_processed=round(stats.total_amount_processed, 2),
        last_processed_at=stats.last_processed_at,
        uptime_seconds=stats.uptime_seconds,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=service_config.settings.service_port,
        reload=service_config.settings.debug,
    )
