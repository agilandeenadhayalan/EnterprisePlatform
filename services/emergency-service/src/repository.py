"""
Emergency repository — in-memory alerts and responders storage.

Manages SOS alerts and emergency responder coordination.
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from models import EmergencyAlert, Responder, EmergencyType, AlertStatus


# Pre-seeded responders
DEFAULT_RESPONDERS = [
    {"id": "resp-001", "name": "Unit Alpha", "type": "police", "status": "available", "location": {"lat": 40.7128, "lng": -74.0060}},
    {"id": "resp-002", "name": "Ambulance 7", "type": "medical", "status": "available", "location": {"lat": 40.7580, "lng": -73.9855}},
    {"id": "resp-003", "name": "Tow Truck 3", "type": "roadside", "status": "available", "location": {"lat": 40.7489, "lng": -73.9680}},
    {"id": "resp-004", "name": "Unit Bravo", "type": "police", "status": "available", "location": {"lat": 40.7282, "lng": -73.7949}},
]


class EmergencyRepository:
    """In-memory emergency alerts and responders storage."""

    def __init__(self):
        self._alerts: dict[str, EmergencyAlert] = {}
        self._responders: dict[str, Responder] = {}
        # Seed default responders
        for r in DEFAULT_RESPONDERS:
            self._responders[r["id"]] = Responder(**r)

    # ── Alerts ──

    def create_sos(
        self,
        emergency_type: str,
        reporter_id: Optional[str] = None,
        location: Optional[dict[str, Any]] = None,
        description: Optional[str] = None,
    ) -> EmergencyAlert:
        """Trigger an SOS alert."""
        alert_id = str(uuid.uuid4())
        alert = EmergencyAlert(
            id=alert_id,
            emergency_type=emergency_type,
            reporter_id=reporter_id,
            location=location,
            description=description,
        )
        self._alerts[alert_id] = alert
        return alert

    def get_alert(self, alert_id: str) -> Optional[EmergencyAlert]:
        """Get an alert by ID."""
        return self._alerts.get(alert_id)

    def list_alerts(self) -> list[EmergencyAlert]:
        """List active emergency alerts (non-resolved)."""
        return [a for a in self._alerts.values() if a.status != "resolved"]

    def update_alert(self, alert_id: str, **fields) -> Optional[EmergencyAlert]:
        """Update specific fields on an alert."""
        alert = self._alerts.get(alert_id)
        if not alert:
            return None
        for key, value in fields.items():
            if value is not None and hasattr(alert, key):
                setattr(alert, key, value)
        return alert

    def dispatch_responder(self, alert_id: str, responder_id: str) -> Optional[EmergencyAlert]:
        """Dispatch a responder to an alert."""
        alert = self._alerts.get(alert_id)
        if not alert:
            return None
        responder = self._responders.get(responder_id)
        if not responder:
            return None
        alert.dispatched_responder = responder_id
        alert.status = "dispatched"
        responder.status = "dispatched"
        return alert

    def resolve_alert(self, alert_id: str) -> Optional[EmergencyAlert]:
        """Resolve an emergency alert."""
        alert = self._alerts.get(alert_id)
        if not alert:
            return None
        alert.status = "resolved"
        alert.resolved_at = datetime.utcnow()
        # Free up the responder
        if alert.dispatched_responder:
            responder = self._responders.get(alert.dispatched_responder)
            if responder:
                responder.status = "available"
        return alert

    # ── Responders ──

    def list_responders(self) -> list[Responder]:
        """List all responders."""
        return list(self._responders.values())

    def get_responder(self, responder_id: str) -> Optional[Responder]:
        """Get a responder by ID."""
        return self._responders.get(responder_id)


# Singleton repository instance
repo = EmergencyRepository()
