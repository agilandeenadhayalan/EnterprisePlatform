"""
Pydantic request/response schemas for the search service API.
"""

from typing import Optional, List, Dict

from pydantic import BaseModel, Field


# ── Request schemas ──

class SearchRequest(BaseModel):
    """POST /search — perform a search query."""
    query: str = Field(..., min_length=1, description="Search query text")
    entity_type: Optional[str] = Field(None, description="Filter by type: driver, rider, trip, vehicle")
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)


class NearbySearchRequest(BaseModel):
    """POST /search/nearby — search for entities near a location."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    radius_km: float = Field(5.0, gt=0, le=50)
    entity_type: Optional[str] = Field(None, description="Filter by type: driver, vehicle, station")
    limit: int = Field(20, ge=1, le=100)


# ── Response schemas ──

class SearchResultItem(BaseModel):
    """Single search result."""
    id: str
    entity_type: str
    title: str
    description: Optional[str] = None
    score: float = 0.0
    metadata: Dict = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """POST /search — search results."""
    results: List[SearchResultItem]
    total: int
    query: str


class SuggestionResponse(BaseModel):
    """GET /search/suggestions — search suggestions."""
    suggestions: List[str]
    query: str
