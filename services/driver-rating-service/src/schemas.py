"""
Pydantic request/response schemas for the driver rating service API.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RatingCreateRequest(BaseModel):
    """POST /ratings — submit a rating."""
    driver_id: str
    rider_id: str
    trip_id: str
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=1000)


class RatingResponse(BaseModel):
    """Individual rating record."""
    id: str
    driver_id: str
    rider_id: str
    trip_id: str
    rating: int
    comment: Optional[str] = None
    created_at: datetime


class RatingListResponse(BaseModel):
    """GET /drivers/{id}/ratings response."""
    ratings: list[RatingResponse]
    total: int


class RatingSummaryResponse(BaseModel):
    """GET /drivers/{id}/rating/summary response."""
    driver_id: str
    average_rating: float
    total_ratings: int
    rating_distribution: dict[str, int]
