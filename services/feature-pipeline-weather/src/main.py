"""
Feature Pipeline Weather — FastAPI application.

Weather feature extraction pipeline. Computes weather features from
external weather API data for use in demand forecasting and pricing models.

ROUTES:
  POST /pipeline/weather/run      — Run weather feature pipeline
  GET  /pipeline/weather/features — Get weather features for location+time
  GET  /pipeline/weather/catalog  — List all weather features
  GET  /health                    — Health check (provided by create_app)
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
    description="Weather feature extraction pipeline for the ML platform",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/pipeline/weather/run", response_model=schemas.PipelineRunResponse)
async def run_pipeline(req: schemas.PipelineRunRequest | None = None):
    """Run the weather feature computation pipeline."""
    station_ids = req.station_ids if req else None
    run = repository.repo.run_pipeline(station_ids=station_ids)
    return schemas.PipelineRunResponse(**run)


@app.get("/pipeline/weather/features", response_model=schemas.WeatherFeatureSetListResponse)
async def get_weather_features(
    station_id: str = Query(description="Weather station ID"),
    hour: Optional[str] = Query(default=None, description="Specific hour (ISO 8601)"),
):
    """Get weather features for a station, optionally filtered by hour."""
    results = repository.repo.get_features(station_id, hour=hour)
    if not results:
        raise HTTPException(status_code=404, detail=f"No weather features found for station '{station_id}'")
    return schemas.WeatherFeatureSetListResponse(
        feature_sets=[schemas.WeatherFeatureSetResponse(**fs.to_dict()) for fs in results],
        total=len(results),
    )


@app.get("/pipeline/weather/catalog", response_model=schemas.CatalogResponse)
async def feature_catalog():
    """List all weather features in the catalog."""
    catalog = repository.repo.get_catalog()
    return schemas.CatalogResponse(
        features=[schemas.CatalogEntry(**c) for c in catalog],
        total=len(catalog),
    )
