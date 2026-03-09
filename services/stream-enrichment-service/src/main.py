"""
Stream Enrichment Service — FastAPI application.

Enriches raw events with dimension lookups (zone names, weather data).

ROUTES:
  POST /enrich               — Enrich a batch of events with dimension data
  GET  /dimensions            — List cached dimensions
  POST /dimensions/refresh    — Refresh dimension cache
  GET  /health                — Health check (provided by create_app)
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
_repo = repository.EnrichmentRepository()


def get_repo() -> repository.EnrichmentRepository:
    """Dependency — returns the enrichment repository."""
    return _repo


@asynccontextmanager
async def lifespan(app):
    """Startup: load dimension caches. Shutdown: cleanup."""
    _repo.refresh_dimensions()
    app.state.repo = _repo
    yield


app = create_app(
    title="Stream Enrichment Service",
    version="0.1.0",
    description="Enriches raw events with dimension lookups (zone names, weather data)",
    lifespan=lifespan,
)


# -- Routes --


@app.post("/enrich", response_model=schemas.EnrichBatchResponse)
async def enrich_batch(
    body: schemas.EnrichBatchRequest,
    repo: repository.EnrichmentRepository = Depends(get_repo),
):
    """Enrich a batch of events with dimension data (zones, weather)."""
    results, failed = repo.enrich_batch(body.events)
    return schemas.EnrichBatchResponse(
        enriched=len(results),
        failed=failed,
        results=[
            schemas.EnrichedEventResponse(
                event_id=r.event_id,
                event_type=r.event_type,
                pickup_zone_name=r.pickup_zone_name,
                pickup_borough=r.pickup_borough,
                dropoff_zone_name=r.dropoff_zone_name,
                dropoff_borough=r.dropoff_borough,
                weather_condition=r.weather_condition,
                temperature_f=r.temperature_f,
                precipitation=r.precipitation,
                enriched_at=r.enriched_at,
                payload=r.payload,
            )
            for r in results
        ],
    )


@app.get("/dimensions", response_model=schemas.DimensionCacheResponse)
async def get_dimensions(
    repo: repository.EnrichmentRepository = Depends(get_repo),
):
    """List cached dimension data."""
    cache = repo.get_dimensions()
    return schemas.DimensionCacheResponse(
        zone_count=cache.zone_count,
        weather_count=cache.weather_count,
        last_refreshed_at=cache.last_refreshed_at,
        zones=cache.zones,
        weather=cache.weather,
    )


@app.post("/dimensions/refresh", response_model=schemas.RefreshResponse)
async def refresh_dimensions(
    repo: repository.EnrichmentRepository = Depends(get_repo),
):
    """Refresh the dimension cache from data sources."""
    zones_loaded, weather_loaded = repo.refresh_dimensions()
    return schemas.RefreshResponse(
        zones_loaded=zones_loaded,
        weather_loaded=weather_loaded,
        status="refreshed",
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=service_config.settings.service_port,
        reload=service_config.settings.debug,
    )
