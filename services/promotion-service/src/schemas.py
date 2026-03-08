"""Pydantic schemas for the promotion service API."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CreatePromotionRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    promotion_type: str = Field(..., description="referral, seasonal, loyalty")
    reward_type: str = Field(..., description="percentage, fixed, free_ride")
    reward_value: float = Field(..., gt=0)
    max_redemptions: Optional[int] = Field(None, gt=0)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class RedeemPromotionRequest(BaseModel):
    user_id: str


class PromotionResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    promotion_type: str
    reward_type: str
    reward_value: float
    max_redemptions: Optional[int] = None
    current_redemptions: int
    is_active: bool
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_at: datetime


class PromotionListResponse(BaseModel):
    promotions: list[PromotionResponse]
    count: int


class RedeemResponse(BaseModel):
    promotion_id: str
    user_id: str
    reward_type: str
    reward_value: float
    redeemed: bool
    message: str
