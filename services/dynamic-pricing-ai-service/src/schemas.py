"""Pydantic schemas for the dynamic pricing AI service API."""

from typing import Optional

from pydantic import BaseModel, Field


class PredictPriceRequest(BaseModel):
    """POST /predict-price — predict optimal price."""
    pickup_lat: float = Field(..., ge=-90, le=90)
    pickup_lon: float = Field(..., ge=-180, le=180)
    dropoff_lat: float = Field(..., ge=-90, le=90)
    dropoff_lon: float = Field(..., ge=-180, le=180)
    vehicle_type: str = Field(default="economy")
    hour_of_day: int = Field(..., ge=0, le=23)
    day_of_week: int = Field(..., ge=0, le=6)
    is_holiday: bool = Field(default=False)


class PredictPriceResponse(BaseModel):
    predicted_fare: float
    confidence: float
    surge_recommendation: float
    model_version: str


class HeatmapCell(BaseModel):
    lat: float
    lon: float
    intensity: float


class HeatmapResponse(BaseModel):
    heatmap: list[HeatmapCell]
    generated_at: str
    grid_size: int
