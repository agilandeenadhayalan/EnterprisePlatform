"""Pydantic schemas for ride feedback service."""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class CreateFeedbackRequest(BaseModel):
    trip_id: str
    rider_id: str
    driver_id: str
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None
    feedback_type: str = "rider_to_driver"


class FeedbackResponse(BaseModel):
    id: str
    trip_id: str
    rider_id: str
    driver_id: str
    rating: int
    comment: Optional[str] = None
    feedback_type: str
    created_at: Optional[datetime] = None


class FeedbackListResponse(BaseModel):
    feedback: List[FeedbackResponse]
    count: int
    average_rating: Optional[float] = None
