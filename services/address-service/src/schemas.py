"""
Pydantic request/response schemas for the address service API.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# -- Response schemas --

class AddressResponse(BaseModel):
    """Address data returned from the API."""
    id: str
    user_id: str
    label: str
    line1: str
    line2: Optional[str] = None
    city: str
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_default: bool
    created_at: datetime
    updated_at: datetime


# -- Request schemas --

class CreateAddressRequest(BaseModel):
    """POST /addresses — add a new address."""
    label: str = Field(..., min_length=1, max_length=50, description="e.g. home, work, gym")
    line1: str = Field(..., min_length=1, max_length=255)
    line2: Optional[str] = Field(None, max_length=255)
    city: str = Field(..., min_length=1, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: str = Field(..., min_length=1, max_length=100)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    is_default: bool = False


class UpdateAddressRequest(BaseModel):
    """PUT /addresses/{address_id} — update an address."""
    label: Optional[str] = Field(None, min_length=1, max_length=50)
    line1: Optional[str] = Field(None, min_length=1, max_length=255)
    line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, min_length=1, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, min_length=1, max_length=100)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
