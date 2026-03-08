"""
Email service repository — stubbed email provider.

In production, this would integrate with SendGrid, AWS SES, or SMTP.
For now, it simulates sending and returns mock message IDs.
"""

import uuid
from typing import Dict, List, Optional


# Stubbed email templates
TEMPLATES = [
    {
        "id": "welcome",
        "name": "Welcome Email",
        "subject": "Welcome to Smart Mobility!",
        "description": "Sent to new users after registration",
    },
    {
        "id": "ride-receipt",
        "name": "Ride Receipt",
        "subject": "Your Ride Receipt",
        "description": "Sent after ride completion with fare details",
    },
    {
        "id": "password-reset",
        "name": "Password Reset",
        "subject": "Reset Your Password",
        "description": "Sent when user requests a password reset",
    },
]


class EmailRepository:
    """Stubbed email provider."""

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        is_html: bool = False,
    ) -> str:
        """Send an email. Returns message_id."""
        message_id = str(uuid.uuid4())
        # In production: send via SMTP/API
        return message_id

    async def send_template_email(
        self,
        to: str,
        template_id: str,
        variables: Dict[str, str],
    ) -> str:
        """Send a templated email. Returns message_id."""
        message_id = str(uuid.uuid4())
        # In production: render template with variables and send
        return message_id

    async def get_templates(self) -> List[Dict]:
        """Get available email templates."""
        return TEMPLATES
