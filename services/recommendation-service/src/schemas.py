"""
Pydantic response schemas for the Recommendation service.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


# ── Request schemas ──

class ColdStartRequest(BaseModel):
    user_type: str
    initial_preferences: Dict[str, Any] = {}


# ── Response schemas ──

class RecommendationResponse(BaseModel):
    entity_id: str
    items: List[str]
    scores: List[float]
    strategy: str
    generated_at: str


class SimilarEntityResponse(BaseModel):
    entity_id: str
    similarity_score: float


class SimilarDriversResponse(BaseModel):
    driver_id: str
    similar_drivers: List[SimilarEntityResponse]
    total: int


class PopularZone(BaseModel):
    zone_id: str
    score: float
    avg_fare: float
    demand_level: str


class PopularZonesResponse(BaseModel):
    zones: List[PopularZone]
    hour: Optional[int] = None
    day: Optional[int] = None
    total: int
