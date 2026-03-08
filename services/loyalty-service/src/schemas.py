"""
Pydantic request/response schemas for the loyalty service API.
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


# ── Request schemas ──

class EarnPointsRequest(BaseModel):
    """POST /loyalty/{user_id}/earn — earn loyalty points."""
    points: int = Field(..., gt=0, description="Points to earn")
    description: Optional[str] = Field(None, description="Reason for earning points")
    reference_id: Optional[str] = Field(None, description="Reference ID (e.g., trip_id)")


class RedeemPointsRequest(BaseModel):
    """POST /loyalty/{user_id}/redeem — redeem loyalty points."""
    points: int = Field(..., gt=0, description="Points to redeem")
    description: Optional[str] = Field(None, description="What the points are redeemed for")
    reference_id: Optional[str] = Field(None, description="Reference ID")


# ── Response schemas ──

class LoyaltyBalanceResponse(BaseModel):
    """GET /loyalty/{user_id} — user's loyalty balance."""
    user_id: str
    total_points: int
    tier: str
    lifetime_points: int


class LoyaltyTransactionResponse(BaseModel):
    """Single loyalty transaction."""
    id: str
    user_id: str
    points: int
    transaction_type: str
    description: Optional[str] = None
    reference_id: Optional[str] = None
    created_at: datetime


class LoyaltyTransactionListResponse(BaseModel):
    """List of loyalty transactions."""
    transactions: List[LoyaltyTransactionResponse]
    count: int


class LoyaltyTierResponse(BaseModel):
    """GET /loyalty/{user_id}/tier — user's tier info."""
    user_id: str
    tier: str
    lifetime_points: int
    next_tier: Optional[str] = None
    points_to_next_tier: Optional[int] = None


class EarnRedeemResponse(BaseModel):
    """Response after earning or redeeming points."""
    user_id: str
    points_changed: int
    new_balance: int
    tier: str
    message: str
