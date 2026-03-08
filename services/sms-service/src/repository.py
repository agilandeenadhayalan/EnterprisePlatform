"""
SMS service repository — stubbed SMS provider.

In production, this would integrate with Twilio, AWS SNS, etc.
For now, it simulates sending and returns mock message IDs.
"""

import uuid
from typing import Dict, Optional


class SmsRepository:
    """Stubbed SMS provider."""

    def __init__(self):
        self._status_store: Dict[str, Dict] = {}

    async def send_sms(self, to: str, message: str) -> str:
        """Send an SMS message. Returns message_id."""
        message_id = str(uuid.uuid4())
        self._status_store[message_id] = {"status": "delivered", "to": to}
        return message_id

    async def send_otp_sms(self, to: str, otp_code: str) -> str:
        """Send an OTP code via SMS. Returns message_id."""
        message = f"Your verification code is: {otp_code}"
        return await self.send_sms(to, message)

    async def get_status(self, message_id: str) -> Optional[Dict]:
        """Get delivery status of an SMS."""
        return self._status_store.get(message_id)
