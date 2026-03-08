"""
Pydantic request/response schemas for the preferences service API.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


# -- Response schemas --

class PreferenceResponse(BaseModel):
    """A single preference key-value pair."""
    category: str
    key: str
    value: Any = None
    updated_at: Optional[datetime] = None


class PreferenceListResponse(BaseModel):
    """All preferences for a user."""
    user_id: str
    preferences: list[PreferenceResponse]


# -- Request schemas --

class SetPreferenceRequest(BaseModel):
    """PUT /preferences/{user_id}/{category}/{key} — set a preference value."""
    value: Any
