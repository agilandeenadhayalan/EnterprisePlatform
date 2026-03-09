"""
Stream Processor Metrics — FastAPI application.

Aggregates business metrics using tumbling windows and writes to ClickHouse fact_stream_metrics.

ROUTES:
  POST /process          — Process metric events
  GET  /windows          — Active tumbling windows
  POST /windows/flush    — Force close and flush all windows
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
_repo = repository.MetricsProcessorRepository(
    window_size_seconds=service_config.settings.window_size_seconds,
)


def get_repo() -> repository.MetricsProcessorRepository:
    """Dependency — returns the metrics processor repository."""
    return _repo


@asynccontextmanager
async def lifespan(app):
    """Startup: initialize clients. Shutdown: flush windows and cleanup."""
    app.state.repo = _repo
    yield
    # Flush remaining windows on shutdown
    _repo.flush_all_windows()


app = create_app(
    title="Stream Processor Metrics",
    version="0.1.0",
    description="Tumbling window aggregation for business metrics — writes to ClickHouse fact_stream_metrics",
    lifespan=lifespan,
)


# -- Routes --


@app.post("/process", response_model=schemas.ProcessBatchResponse)
async def process_batch(
    body: schemas.ProcessBatchRequest,
    repo: repository.MetricsProcessorRepository = Depends(get_repo),
):
    """Process a batch of metric events into tumbling windows."""
    accepted, failed, windows_updated = repo.process_batch(body.events)
    return schemas.ProcessBatchResponse(
        accepted=accepted,
        failed=failed,
        windows_updated=windows_updated,
    )


@app.get("/windows", response_model=schemas.ActiveWindowsResponse)
async def get_windows(
    repo: repository.MetricsProcessorRepository = Depends(get_repo),
):
    """Return active tumbling windows."""
    windows = repo.get_active_windows()
    return schemas.ActiveWindowsResponse(
        active_windows=[
            schemas.WindowStateResponse(
                window_key=w.window_key,
                metric_name=w.metric_name,
                window_start=w.window_start,
                window_end=w.window_end,
                event_count=w.event_count,
                current_sum=w.current_sum,
                current_min=w.current_min,
                current_max=w.current_max,
                is_open=w.is_open,
            )
            for w in windows
        ],
        total=len(windows),
    )


@app.post("/windows/flush", response_model=schemas.FlushResponse)
async def flush_windows(
    repo: repository.MetricsProcessorRepository = Depends(get_repo),
):
    """Force close and flush all active windows."""
    aggregates = repo.flush_all_windows()
    return schemas.FlushResponse(
        flushed=len(aggregates),
        aggregates=[
            schemas.WindowedAggregateResponse(
                window_key=a.window_key,
                metric_name=a.metric_name,
                window_start=a.window_start.isoformat(),
                window_end=a.window_end.isoformat(),
                count=a.count,
                sum_value=a.sum_value,
                avg_value=a.avg_value,
                min_value=a.min_value,
                max_value=a.max_value,
            )
            for a in aggregates
        ],
    )


@app.get("/process/stats", response_model=schemas.ProcessingStatsResponse)
async def get_stats(
    repo: repository.MetricsProcessorRepository = Depends(get_repo),
):
    """Return processing statistics."""
    stats = repo.get_stats()
    return schemas.ProcessingStatsResponse(**stats)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=service_config.settings.service_port,
        reload=service_config.settings.debug,
    )
