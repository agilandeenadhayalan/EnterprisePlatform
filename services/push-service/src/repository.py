"""
Push service repository — stubbed push provider.

In production, this would integrate with Firebase Cloud Messaging (FCM),
Apple Push Notification Service (APNs), etc. For now, it simulates
sending and returns mock message IDs.
"""

import uuid
from typing import Dict, List, Optional


class PushRepository:
    """Stubbed push notification provider."""

    def __init__(self):
        self._status_store: Dict[str, str] = {}

    async def send_push(
        self,
        device_token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
    ) -> str:
        """Send a push notification to a single device. Returns message_id."""
        message_id = str(uuid.uuid4())
        self._status_store[message_id] = "delivered"
        return message_id

    async def send_push_bulk(
        self,
        device_tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
    ) -> tuple[List[str], int, int]:
        """Send push to multiple devices. Returns (message_ids, sent_count, failed_count)."""
        message_ids = []
        sent = 0
        failed = 0
        for token in device_tokens:
            msg_id = str(uuid.uuid4())
            message_ids.append(msg_id)
            self._status_store[msg_id] = "delivered"
            sent += 1
        return message_ids, sent, failed

    async def get_status(self, message_id: str) -> Optional[str]:
        """Get delivery status of a push notification."""
        return self._status_store.get(message_id)
