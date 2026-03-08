"""
Pydantic request/response schemas for the profile service API.
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


# -- Response schemas --

class ProfileResponse(BaseModel):
    """User profile data."""
    user_id: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    date_of_birth: Optional[date] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# -- Request schemas --

class CreateProfileRequest(BaseModel):
    """PUT /profiles/{user_id} — create or replace a profile."""
    avatar_url: Optional[str] = Field(None, max_length=512)
    bio: Optional[str] = Field(None, max_length=2000)
    date_of_birth: Optional[date] = None
    language: Optional[str] = Field(None, max_length=10)
    timezone: Optional[str] = Field(None, max_length=50)


class UpdateProfileRequest(BaseModel):
    """PATCH /profiles/{user_id} — partial update of profile fields."""
    avatar_url: Optional[str] = Field(None, max_length=512)
    bio: Optional[str] = Field(None, max_length=2000)
    date_of_birth: Optional[date] = None
    language: Optional[str] = Field(None, max_length=10)
    timezone: Optional[str] = Field(None, max_length=50)
