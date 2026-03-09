"""
Stream Dedup Service — FastAPI application.

Deduplicates events using a sliding window with in-memory sets (simulating Redis).

ROUTES:
  POST   /dedup          — Check and deduplicate a batch of events
  GET    /dedup/stats     — Hit rate, miss rate, cache size, total checked
  DELETE /dedup/cache     — Clear dedup cache
  GET    /health          — Health check (provided by create_app)
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
_repo = repository.DedupRepository(
    window_seconds=service_config.settings.window_seconds,
    max_cache_size=service_config.settings.max_cache_size,
)


def get_repo() -> repository.DedupRepository:
    """Dependency — returns the dedup repository."""
    return _repo


@asynccontextmanager
async def lifespan(app):
    """Startup: initialize dedup cache. Shutdown: cleanup."""
    app.state.repo = _repo
    yield


app = create_app(
    title="Stream Dedup Service",
    version="0.1.0",
    description="Deduplicates events using sliding window with in-memory sets",
    lifespan=lifespan,
)


# -- Routes --


@app.post("/dedup", response_model=schemas.DedupBatchResponse)
async def dedup_batch(
    body: schemas.DedupBatchRequest,
    repo: repository.DedupRepository = Depends(get_repo),
):
    """Check and deduplicate a batch of events. Returns only unique events."""
    unique_events, duplicate_ids = repo.check_and_dedup(
        body.events, body.event_id_field
    )
    return schemas.DedupBatchResponse(
        unique_events=unique_events,
        duplicate_event_ids=duplicate_ids,
        unique_count=len(unique_events),
        duplicate_count=len(duplicate_ids),
        total_checked=len(body.events),
    )


@app.get("/dedup/stats", response_model=schemas.DedupStatsResponse)
async def get_stats(
    repo: repository.DedupRepository = Depends(get_repo),
):
    """Return deduplication statistics."""
    stats = repo.get_stats()
    return schemas.DedupStatsResponse(**stats)


@app.delete("/dedup/cache", response_model=schemas.ClearCacheResponse)
async def clear_cache(
    repo: repository.DedupRepository = Depends(get_repo),
):
    """Clear the dedup cache."""
    cleared = repo.clear_cache()
    return schemas.ClearCacheResponse(
        cleared=cleared,
        status="cleared",
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=service_config.settings.service_port,
        reload=service_config.settings.debug,
    )
