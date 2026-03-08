"""Pydantic schemas for route service."""

from typing import Optional

from pydantic import BaseModel, Field


class RouteCalculateRequest(BaseModel):
    pickup_latitude: float = Field(..., ge=-90, le=90)
    pickup_longitude: float = Field(..., ge=-180, le=180)
    dropoff_latitude: float = Field(..., ge=-90, le=90)
    dropoff_longitude: float = Field(..., ge=-180, le=180)


class RouteCalculateResponse(BaseModel):
    straight_line_distance_km: float
    estimated_road_distance_km: float
    estimated_duration_minutes: int
    average_speed_kmh: float


class EtaRequest(BaseModel):
    origin_latitude: float = Field(..., ge=-90, le=90)
    origin_longitude: float = Field(..., ge=-180, le=180)
    destination_latitude: float = Field(..., ge=-90, le=90)
    destination_longitude: float = Field(..., ge=-180, le=180)


class EtaResponse(BaseModel):
    eta_minutes: int
    distance_km: float
