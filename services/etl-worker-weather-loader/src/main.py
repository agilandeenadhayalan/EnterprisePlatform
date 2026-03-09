"""
ETL Worker Weather Loader Service

Loads NOAA weather data into ClickHouse dim_weather table.
Handles CSV parsing, unit conversions (Celsius to Fahrenheit),
and missing data handling for NYC-area weather stations.

Routes:
    POST /load          — Load weather data for a date range
    GET  /load/status   — Loading status
    GET  /stations      — List weather stations
    GET  /health        — Health check (provided by create_app)
"""

import random
import sys
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import HTTPException

from mobility_common.fastapi.app import create_app

import config as service_config
import schemas
import repository


@asynccontextmanager
async def lifespan(app):
    yield


app = create_app(service_config.settings.service_name, lifespan=lifespan)
repo = repository.weather_loader_repo


@app.post("/load", response_model=schemas.LoadJobResponse, tags=["Load"])
async def load_weather_data(request: schemas.LoadRequest):
    """Load NOAA weather data for a given date range."""
    if request.end_date < request.start_date:
        raise HTTPException(status_code=400, detail="end_date must be after start_date")

    job = repo.create_load_job(start_date=request.start_date, end_date=request.end_date)

    # Simulate loading with station processing
    days = (request.end_date - request.start_date).days + 1
    stations_count = len(request.station_ids) if request.station_ids else repo.get_station_count()
    rows = days * stations_count * random.randint(1, 5)
    repo.complete_job(job.job_id, rows_loaded=rows, stations_processed=stations_count)

    completed = repo.get_job(job.job_id)
    return schemas.LoadJobResponse(
        job_id=completed.job_id,
        start_date=completed.start_date,
        end_date=completed.end_date,
        state=completed.state.value,
        rows_loaded=completed.rows_loaded,
        stations_processed=completed.stations_processed,
        started_at=completed.started_at,
        completed_at=completed.completed_at,
    )


@app.get("/load/status", response_model=schemas.LoadStatusResponse, tags=["Load"])
async def load_status():
    """Get loading status for all weather data jobs."""
    active = repo.get_active_jobs()
    completed_count = len(repo.get_completed_jobs())
    total_rows = repo.get_total_rows_loaded()

    active_responses = [
        schemas.LoadJobResponse(
            job_id=j.job_id,
            start_date=j.start_date,
            end_date=j.end_date,
            state=j.state.value,
            rows_loaded=j.rows_loaded,
            stations_processed=j.stations_processed,
            started_at=j.started_at,
            completed_at=j.completed_at,
        )
        for j in active
    ]

    return schemas.LoadStatusResponse(
        active_jobs=active_responses,
        completed_jobs=completed_count,
        total_rows_loaded=total_rows,
    )


@app.get("/stations", response_model=schemas.StationsListResponse, tags=["Stations"])
async def list_stations():
    """List all available NOAA weather stations."""
    stations = repo.get_all_stations()
    station_responses = [
        schemas.WeatherStationResponse(
            station_id=s.station_id,
            name=s.name,
            latitude=s.latitude,
            longitude=s.longitude,
            elevation_m=s.elevation_m,
            state=s.state,
            country=s.country,
        )
        for s in stations
    ]
    return schemas.StationsListResponse(stations=station_responses, total=len(station_responses))
