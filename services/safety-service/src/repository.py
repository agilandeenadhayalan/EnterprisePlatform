"""
Safety repository — in-memory safety scores and alerts storage.

Manages driver/rider safety scores and safety alerts.
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from models import SafetyScore, SafetyAlert, EntityType


class SafetyRepository:
    """In-memory safety scores and alerts storage."""

    def __init__(self):
        self._scores: dict[str, SafetyScore] = {}
        self._score_history: dict[str, list[SafetyScore]] = {}  # "entity_type:entity_id" -> list
        self._alerts: dict[str, SafetyAlert] = {}

    # ── Safety Scores ──

    def create_score(
        self,
        entity_type: str,
        entity_id: str,
        score: float,
        factors: Optional[dict[str, Any]] = None,
    ) -> SafetyScore:
        """Calculate/record a safety score."""
        score_id = str(uuid.uuid4())
        safety_score = SafetyScore(
            id=score_id,
            entity_type=entity_type,
            entity_id=entity_id,
            score=score,
            factors=factors,
        )
        key = f"{entity_type}:{entity_id}"
        self._scores[key] = safety_score
        self._score_history.setdefault(key, []).append(safety_score)
        return safety_score

    def get_score(self, entity_type: str, entity_id: str) -> Optional[SafetyScore]:
        """Get current safety score for an entity."""
        key = f"{entity_type}:{entity_id}"
        return self._scores.get(key)

    def list_scores(self) -> list[SafetyScore]:
        """List all current safety scores."""
        return list(self._scores.values())

    def get_score_history(self, entity_type: str, entity_id: str) -> list[SafetyScore]:
        """Get score history for an entity."""
        key = f"{entity_type}:{entity_id}"
        return self._score_history.get(key, [])

    # ── Safety Alerts ──

    def create_alert(
        self,
        entity_type: str,
        entity_id: str,
        alert_type: str,
        severity: str,
        message: str,
    ) -> SafetyAlert:
        """Create a safety alert."""
        alert_id = str(uuid.uuid4())
        alert = SafetyAlert(
            id=alert_id,
            entity_type=entity_type,
            entity_id=entity_id,
            alert_type=alert_type,
            severity=severity,
            message=message,
        )
        self._alerts[alert_id] = alert
        return alert

    def get_alert(self, alert_id: str) -> Optional[SafetyAlert]:
        """Get an alert by ID."""
        return self._alerts.get(alert_id)

    def list_alerts(self) -> list[SafetyAlert]:
        """List all safety alerts."""
        return list(self._alerts.values())

    def update_alert(self, alert_id: str, **fields) -> Optional[SafetyAlert]:
        """Update specific fields on an alert."""
        alert = self._alerts.get(alert_id)
        if not alert:
            return None
        for key, value in fields.items():
            if value is not None and hasattr(alert, key):
                setattr(alert, key, value)
        return alert


# Singleton repository instance
repo = SafetyRepository()
