"""
Feature Pipeline Zone — FastAPI application.

Zone/geospatial feature pipeline. Computes per-zone features from ride data,
driver location data, and pricing engine output.

ROUTES:
  POST /pipeline/zone/run                         — Run zone feature pipeline
  GET  /pipeline/zone/features/{zone_id}           — Get zone features
  GET  /pipeline/zone/features/{zone_id}/timeseries — Zone features over time
  GET  /pipeline/zone/catalog                      — List all zone features
  GET  /health                                     — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import Query, HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app

import config as service_config
import schemas
import repository


@asynccontextmanager
async def lifespan(app):
    yield


app = create_app(
    title=service_config.settings.service_name,
    version="0.1.0",
    description="Zone/geospatial feature pipeline for the ML platform",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/pipeline/zone/run", response_model=schemas.PipelineRunResponse)
async def run_pipeline(req: schemas.PipelineRunRequest | None = None):
    """Run the zone feature computation pipeline."""
    zone_ids = req.zone_ids if req else None
    run = repository.repo.run_pipeline(zone_ids=zone_ids)
    return schemas.PipelineRunResponse(**run)


@app.get("/pipeline/zone/features/{zone_id}", response_model=schemas.ZoneFeatureSetResponse)
async def get_zone_features(zone_id: str):
    """Get the latest computed features for a zone."""
    fs = repository.repo.get_features(zone_id)
    if not fs:
        raise HTTPException(status_code=404, detail=f"No features found for zone '{zone_id}'")
    return schemas.ZoneFeatureSetResponse(**fs.to_dict())


@app.get("/pipeline/zone/features/{zone_id}/timeseries", response_model=schemas.TimeseriesResponse)
async def get_zone_timeseries(
    zone_id: str,
    start_hour: Optional[str] = Query(default=None, description="Start hour (ISO 8601)"),
    end_hour: Optional[str] = Query(default=None, description="End hour (ISO 8601)"),
):
    """Get zone features over time as a timeseries."""
    results = repository.repo.get_timeseries(zone_id, start_hour=start_hour, end_hour=end_hour)
    if not results:
        raise HTTPException(status_code=404, detail=f"No timeseries data found for zone '{zone_id}'")
    return schemas.TimeseriesResponse(
        zone_id=zone_id,
        timeseries=[schemas.ZoneFeatureSetResponse(**fs.to_dict()) for fs in results],
        total=len(results),
    )


@app.get("/pipeline/zone/catalog", response_model=schemas.CatalogResponse)
async def feature_catalog():
    """List all zone features in the catalog."""
    catalog = repository.repo.get_catalog()
    return schemas.CatalogResponse(
        features=[schemas.CatalogEntry(**c) for c in catalog],
        total=len(catalog),
    )
