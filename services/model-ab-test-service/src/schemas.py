"""
Pydantic request/response schemas for the model A/B test API.
"""

from typing import Optional

from pydantic import BaseModel, Field


# ── Request schemas ──


class ABTestCreateRequest(BaseModel):
    """Request to create an A/B test."""
    name: str = Field(..., description="Test name")
    champion_model: str = Field(..., description="Champion model name")
    challenger_model: str = Field(..., description="Challenger model name")
    traffic_split: float = Field(default=0.5, ge=0.0, le=1.0, description="Fraction of traffic to challenger")


class RouteRequest(BaseModel):
    """Request to route a prediction to a variant."""
    request_id: str = Field(..., description="Unique request ID for deterministic routing")


class RecordOutcomeRequest(BaseModel):
    """Record an outcome for a variant."""
    variant: str = Field(..., description="Variant name: champion or challenger")
    value: float = Field(..., description="Outcome value")


# ── Response schemas ──


class ABVariantResponse(BaseModel):
    """A/B test variant details."""
    name: str
    model_name: str
    traffic_pct: float
    request_count: int
    total_value: float
    avg_value: float


class ABTestResponse(BaseModel):
    """A/B test details."""
    id: str
    name: str
    champion_model: str
    challenger_model: str
    traffic_split: float
    status: str
    winner: Optional[str] = None
    created_at: str
    concluded_at: Optional[str] = None
    champion: ABVariantResponse
    challenger: ABVariantResponse


class ABTestListResponse(BaseModel):
    """List of A/B tests."""
    tests: list[ABTestResponse]
    total: int


class RouteResponse(BaseModel):
    """Routing decision for a request."""
    variant: str
    model_name: str
    test_id: str


class SignificanceResponse(BaseModel):
    """Statistical significance result."""
    p_value: float
    is_significant: bool
    recommended_action: str
