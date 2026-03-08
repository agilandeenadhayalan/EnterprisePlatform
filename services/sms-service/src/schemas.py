"""
Pydantic request/response schemas for the SMS service API.
"""

from typing import Optional

from pydantic import BaseModel, Field


# ── Request schemas ──

class SmsSendRequest(BaseModel):
    """POST /sms/send — send an SMS message."""
    to: str = Field(..., description="Recipient phone number (E.164 format)")
    message: str = Field(..., max_length=1600, description="SMS message body")


class SmsSendOtpRequest(BaseModel):
    """POST /sms/send-otp — send an OTP via SMS."""
    to: str = Field(..., description="Recipient phone number (E.164 format)")
    otp_code: str = Field(..., min_length=4, max_length=8, description="OTP code to send")


# ── Response schemas ──

class SmsSendResponse(BaseModel):
    """Response after sending an SMS."""
    message_id: str
    status: str = "queued"
    to: str
    provider: str = "twilio"


class SmsStatusResponse(BaseModel):
    """GET /sms/status/{id} — delivery status of an SMS."""
    message_id: str
    status: str
    to: Optional[str] = None
    delivered_at: Optional[str] = None
