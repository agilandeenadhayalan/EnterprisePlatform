"""
Demand Forecast Service — FastAPI application.

Demand forecasting with weather-adjusted predictions across city zones.

ROUTES:
  GET  /demand/forecasts             — List forecasts
  GET  /demand/forecasts/{id}        — Get forecast
  POST /demand/forecast              — Create forecast
  GET  /demand/zones                 — List grid cells
  GET  /demand/zones/{id}            — Get zone detail
  POST /demand/weather-impact        — Record weather impact
  GET  /demand/stats                 — Demand statistics
  GET  /health                       — Health check (provided by create_app)
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
    description="Demand forecasting with weather-adjusted predictions across city zones",
    lifespan=lifespan,
)


# ── Routes ──


@app.get("/demand/forecasts", response_model=schemas.DemandForecastListResponse)
async def list_forecasts(
    zone_id: Optional[str] = Query(default=None, description="Filter by zone_id"),
    method: Optional[str] = Query(default=None, description="Filter by method"),
):
    """List all demand forecasts."""
    forecasts = repository.repo.list_forecasts(zone_id=zone_id, method=method)
    return schemas.DemandForecastListResponse(
        forecasts=[schemas.DemandForecastResponse(**f.to_dict()) for f in forecasts],
        total=len(forecasts),
    )


@app.get("/demand/forecasts/{fc_id}", response_model=schemas.DemandForecastResponse)
async def get_forecast(fc_id: str):
    """Get a single demand forecast by ID."""
    fc = repository.repo.get_forecast(fc_id)
    if not fc:
        raise HTTPException(status_code=404, detail=f"Forecast '{fc_id}' not found")
    return schemas.DemandForecastResponse(**fc.to_dict())


@app.post("/demand/forecast", response_model=schemas.DemandForecastResponse, status_code=201)
async def create_forecast(req: schemas.DemandForecastCreateRequest):
    """Create a new demand forecast."""
    fc = repository.repo.create_forecast(req.model_dump())
    return schemas.DemandForecastResponse(**fc.to_dict())


@app.get("/demand/zones", response_model=schemas.GridCellListResponse)
async def list_zones():
    """List all grid cells / zones."""
    zones = repository.repo.list_zones()
    return schemas.GridCellListResponse(
        zones=[schemas.GridCellResponse(**z.to_dict()) for z in zones],
        total=len(zones),
    )


@app.get("/demand/zones/{zone_id}", response_model=schemas.GridCellResponse)
async def get_zone(zone_id: str):
    """Get a zone detail."""
    zone = repository.repo.get_zone(zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail=f"Zone '{zone_id}' not found")
    return schemas.GridCellResponse(**zone.to_dict())


@app.post("/demand/weather-impact", response_model=schemas.WeatherImpactResponse, status_code=201)
async def record_weather_impact(req: schemas.WeatherImpactRequest):
    """Record or update a weather impact coefficient."""
    wi = repository.repo.upsert_weather_impact(req.condition, req.impact_coefficient)
    return schemas.WeatherImpactResponse(**wi.to_dict())


@app.get("/demand/stats", response_model=schemas.DemandStatsResponse)
async def demand_stats():
    """Get demand forecast statistics."""
    stats = repository.repo.get_stats()
    return schemas.DemandStatsResponse(**stats)
