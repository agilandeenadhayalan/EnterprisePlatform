"""
Pydantic request/response schemas for the OTP service API.

These define the API contract — what clients send and receive.
The actual OTP code is never returned in responses; only status.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Request schemas ──

class SendOtpRequest(BaseModel):
    """POST /otp/send — request to generate and send an OTP."""
    user_id: str = Field(..., description="UUID of the user to send OTP to")
    channel: str = Field("email", description="Delivery channel: email or sms")
    purpose: str = Field("verification", description="Purpose: verification, login, password_reset")


class VerifyOtpRequest(BaseModel):
    """POST /otp/verify — submit an OTP code for verification."""
    user_id: str = Field(..., description="UUID of the user verifying the OTP")
    code: str = Field(..., min_length=6, max_length=6, description="The 6-digit OTP code")


# ── Response schemas ──

class SendOtpResponse(BaseModel):
    """Response after OTP generation — never includes the actual code."""
    message: str = "OTP sent successfully"
    channel: str
    expires_in_minutes: int


class VerifyOtpResponse(BaseModel):
    """Response after OTP verification attempt."""
    verified: bool
    message: str


class OtpStatusResponse(BaseModel):
    """GET /otp/status/{user_id} — check if a user has a pending OTP."""
    has_pending_otp: bool
    channel: Optional[str] = None
    purpose: Optional[str] = None
    expires_at: Optional[datetime] = None
    attempts_remaining: Optional[int] = None
