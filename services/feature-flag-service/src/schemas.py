"""
Pydantic request/response schemas for the feature flag service API.

These define the API contract — what clients send and receive.
The evaluate endpoint is the most important: it returns whether a flag is
enabled for a specific user, along with a human-readable reason explaining
the decision.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class FlagResponse(BaseModel):
    """Full feature flag details — returned in list and detail endpoints."""
    id: str
    flag_name: str
    description: Optional[str] = None
    is_enabled: bool
    rollout_percentage: int
    target_roles: Optional[list[str]] = None
    metadata: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class CreateFlagRequest(BaseModel):
    """POST /flags — create a new feature flag."""
    flag_name: str = Field(..., min_length=1, max_length=255, description="Unique flag identifier")
    description: Optional[str] = Field(None, description="Human-readable description")
    is_enabled: bool = Field(False, description="Whether the flag is globally enabled")
    rollout_percentage: int = Field(100, ge=0, le=100, description="Percentage of users to roll out to (0-100)")
    target_roles: Optional[list[str]] = Field(None, description="Roles that can see this flag (None = all roles)")
    metadata: Optional[dict[str, Any]] = Field(None, description="Arbitrary metadata")


class UpdateFlagRequest(BaseModel):
    """PUT /flags/{flag_name} — update an existing feature flag."""
    description: Optional[str] = None
    is_enabled: Optional[bool] = None
    rollout_percentage: Optional[int] = Field(None, ge=0, le=100)
    target_roles: Optional[list[str]] = None
    metadata: Optional[dict[str, Any]] = None


class EvaluateFlagResponse(BaseModel):
    """
    GET /flags/evaluate/{flag_name} — result of evaluating a flag for a user.

    The reason field explains WHY the flag was enabled/disabled:
      - "user override: enabled"
      - "flag is globally disabled"
      - "flag enabled, no restrictions"
      - "user role 'rider' not in target roles"
      - "user included in 50% rollout (hash=23)"
      - "user excluded from 50% rollout (hash=78)"
    """
    flag_name: str
    is_enabled: bool
    reason: str


class OverrideRequest(BaseModel):
    """POST /flags/{flag_name}/overrides — set a per-user override."""
    user_id: str = Field(..., description="UUID of the user to override for")
    is_enabled: bool = Field(..., description="Whether to force-enable or force-disable")
    reason: Optional[str] = Field(None, description="Why this override was set")


class OverrideResponse(BaseModel):
    """Response for override operations."""
    id: str
    flag_name: str
    user_id: str
    is_enabled: bool
    reason: Optional[str] = None
    created_at: datetime


class FlagListResponse(BaseModel):
    """GET /flags — list of feature flags."""
    flags: list[FlagResponse]
    count: int
