"""
Pydantic schemas for ETL Worker Weather Loader API request/response validation.
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class LoadRequest(BaseModel):
    start_date: date = Field(..., description="Start date for weather data")
    end_date: date = Field(..., description="End date for weather data")
    station_ids: list[str] = Field(default=[], description="Specific station IDs to load (empty = all)")


class LoadJobResponse(BaseModel):
    job_id: str
    start_date: date
    end_date: date
    state: str
    rows_loaded: int
    stations_processed: int
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class LoadStatusResponse(BaseModel):
    active_jobs: list[LoadJobResponse] = []
    completed_jobs: int = 0
    total_rows_loaded: int = 0


class WeatherStationResponse(BaseModel):
    station_id: str
    name: str
    latitude: float
    longitude: float
    elevation_m: Optional[float] = None
    state: Optional[str] = None
    country: str = "US"


class StationsListResponse(BaseModel):
    stations: list[WeatherStationResponse]
    total: int
