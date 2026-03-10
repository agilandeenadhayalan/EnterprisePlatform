"""
Pydantic response schemas for the Demand Forecast service.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel


class DemandForecastResponse(BaseModel):
    id: str
    zone_id: str
    time_slot: str
    predicted_demand: float
    actual_demand: Optional[float] = None
    uncertainty_low: float
    uncertainty_high: float
    method: str
    weather_factor: float
    created_at: str


class DemandForecastListResponse(BaseModel):
    forecasts: List[DemandForecastResponse]
    total: int


class DemandForecastCreateRequest(BaseModel):
    zone_id: str
    time_slot: str
    method: str = "time_series"


class GridCellResponse(BaseModel):
    id: str
    zone_name: str
    lat: float
    lng: float
    base_demand: float


class GridCellListResponse(BaseModel):
    zones: List[GridCellResponse]
    total: int


class WeatherImpactRequest(BaseModel):
    condition: str
    impact_coefficient: float


class WeatherImpactResponse(BaseModel):
    condition: str
    impact_coefficient: float


class DemandStatsResponse(BaseModel):
    total_forecasts: int
    by_method: Dict[str, int]
    avg_uncertainty_range: float
