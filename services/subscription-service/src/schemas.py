"""
Pydantic request/response schemas for the subscription service API.
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


# ── Request schemas ──

class CreateSubscriptionRequest(BaseModel):
    """POST /subscriptions — create a new subscription."""
    user_id: str = Field(..., description="User ID")
    plan_id: str = Field(..., description="Plan identifier")


# ── Response schemas ──

class SubscriptionResponse(BaseModel):
    """Single subscription response."""
    id: str
    user_id: str
    plan_id: str
    status: str
    price_per_month: float
    started_at: datetime
    expires_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    created_at: datetime


class PlanResponse(BaseModel):
    """Single subscription plan."""
    id: str
    name: str
    price_per_month: float
    description: str
    features: List[str]


class PlanListResponse(BaseModel):
    """GET /plans — available subscription plans."""
    plans: List[PlanResponse]
    count: int


class CancelResponse(BaseModel):
    """Response after cancelling a subscription."""
    id: str
    status: str
    cancelled_at: datetime
    message: str = "Subscription cancelled"
