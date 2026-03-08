"""
Pydantic request/response schemas for the driver matching service API.
"""

from typing import Optional

from pydantic import BaseModel, Field


# -- Request schemas --

class DriverCandidate(BaseModel):
    """A driver candidate for matching."""
    driver_id: str
    latitude: float
    longitude: float
    rating: float = Field(5.0, ge=0, le=5)
    acceptance_rate: float = Field(1.0, ge=0, le=1)
    total_trips: int = Field(0, ge=0)
    vehicle_type: str = "sedan"


class MatchRequest(BaseModel):
    """POST /match — find best driver for a trip."""
    trip_id: str = Field(..., description="Trip UUID")
    pickup_latitude: float = Field(..., ge=-90, le=90)
    pickup_longitude: float = Field(..., ge=-180, le=180)
    vehicle_type_preference: Optional[str] = None
    max_distance_km: float = Field(10.0, gt=0, le=50)
    candidates: list[DriverCandidate] = Field(..., min_length=1)


# -- Response schemas --

class ScoredCandidate(BaseModel):
    """Driver candidate with computed match score."""
    driver_id: str
    distance_km: float
    rating: float
    acceptance_rate: float
    total_trips: int
    vehicle_type: str
    score: float
    rank: int


class MatchResponse(BaseModel):
    """POST /match response."""
    trip_id: str
    best_match: Optional[ScoredCandidate] = None
    candidates: list[ScoredCandidate]
    total_candidates: int
    total_eligible: int


class CandidatesResponse(BaseModel):
    """GET /candidates/{trip_id} response (cached results)."""
    trip_id: str
    candidates: list[ScoredCandidate]
    total: int
