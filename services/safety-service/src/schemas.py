"""
Pydantic request/response schemas for the safety API.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Request schemas ──

class SafetyScoreCreate(BaseModel):
    """POST /safety/scores — calculate/record safety score."""
    entity_type: str = Field(..., description="Entity type: driver, rider")
    entity_id: str = Field(..., description="Entity identifier")
    score: float = Field(..., description="Safety score (0-100)")
    factors: Optional[dict[str, Any]] = Field(default=None, description="Scoring factors")


class AlertCreate(BaseModel):
    """POST /safety/alerts — create safety alert."""
    entity_type: str = Field(..., description="Entity type: driver, rider")
    entity_id: str = Field(..., description="Entity identifier")
    alert_type: str = Field(..., description="Alert type (e.g. speeding, harsh_braking)")
    severity: str = Field(..., description="Severity: low, medium, high, critical")
    message: str = Field(..., description="Alert message")


class AlertUpdate(BaseModel):
    """PATCH /safety/alerts/{id} — update alert status."""
    status: Optional[str] = None
    message: Optional[str] = None


# ── Response schemas ──

class SafetyScoreResponse(BaseModel):
    """A safety score."""
    id: str
    entity_type: str
    entity_id: str
    score: float
    factors: dict[str, Any] = {}
    calculated_at: datetime


class SafetyAlertResponse(BaseModel):
    """A safety alert."""
    id: str
    entity_type: str
    entity_id: str
    alert_type: str
    severity: str
    message: str
    status: str
    created_at: datetime
