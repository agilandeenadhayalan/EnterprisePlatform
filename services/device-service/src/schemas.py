"""
Pydantic request/response schemas for the device service API.

Defines shapes for device registration, trust management, and listing.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# -- Request schemas --

class RegisterDeviceRequest(BaseModel):
    """POST /devices — register a new device."""
    device_id: str = Field(..., description="Client-generated device identifier")
    device_name: str = Field(..., max_length=255, description="Human-readable name, e.g. 'Chrome on MacBook'")
    device_type: Optional[str] = Field(None, max_length=50, description="'mobile', 'desktop', 'tablet'")
    os: Optional[str] = Field(None, max_length=100, description="Operating system, e.g. 'iOS 17.2'")
    browser: Optional[str] = Field(None, max_length=100, description="Browser name, e.g. 'Chrome 120'")
    fingerprint: Optional[str] = Field(None, max_length=255, description="Browser/device fingerprint hash")


class TrustDeviceRequest(BaseModel):
    """PUT /devices/{device_id}/trust — toggle device trust status."""
    is_trusted: bool = Field(..., description="Whether to mark this device as trusted")


# -- Response schemas --

class DeviceResponse(BaseModel):
    """Device data returned from endpoints."""
    id: str
    user_id: str
    device_id: str
    device_name: Optional[str] = None
    device_type: Optional[str] = None
    os: Optional[str] = None
    browser: Optional[str] = None
    fingerprint: Optional[str] = None
    is_trusted: bool = False
    last_used_at: Optional[datetime] = None
    created_at: datetime


class MessageResponse(BaseModel):
    """Simple acknowledgement response."""
    message: str
