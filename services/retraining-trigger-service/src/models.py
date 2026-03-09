"""
Domain models for the Retraining Trigger Service.

Represents retraining triggers, evaluations, and firing history.
"""

from typing import Optional


class RetrainingTrigger:
    """A rule that determines when a model should be retrained."""

    def __init__(
        self,
        id: str,
        model_name: str,
        trigger_type: str,
        condition: str,
        threshold: float,
        cooldown_hours: int,
        is_active: bool = True,
        last_fired_at: Optional[str] = None,
        created_at: str = "2024-01-15T10:00:00Z",
    ):
        self.id = id
        self.model_name = model_name
        self.trigger_type = trigger_type
        self.condition = condition
        self.threshold = threshold
        self.cooldown_hours = cooldown_hours
        self.is_active = is_active
        self.last_fired_at = last_fired_at
        self.created_at = created_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "model_name": self.model_name,
            "trigger_type": self.trigger_type,
            "condition": self.condition,
            "threshold": self.threshold,
            "cooldown_hours": self.cooldown_hours,
            "is_active": self.is_active,
            "last_fired_at": self.last_fired_at,
            "created_at": self.created_at,
        }


class TriggerEvaluation:
    """Result of evaluating a trigger against current metrics."""

    def __init__(
        self,
        trigger_id: str,
        fired: bool,
        reason: str,
        metric_value: float,
        threshold: float,
        evaluated_at: str = "2024-01-15T10:00:00Z",
    ):
        self.trigger_id = trigger_id
        self.fired = fired
        self.reason = reason
        self.metric_value = metric_value
        self.threshold = threshold
        self.evaluated_at = evaluated_at

    def to_dict(self) -> dict:
        return {
            "trigger_id": self.trigger_id,
            "fired": self.fired,
            "reason": self.reason,
            "metric_value": self.metric_value,
            "threshold": self.threshold,
            "evaluated_at": self.evaluated_at,
        }


class TriggerHistory:
    """Record of a trigger firing event."""

    def __init__(
        self,
        trigger_id: str,
        model_name: str,
        fired_at: str,
        reason: str,
    ):
        self.trigger_id = trigger_id
        self.model_name = model_name
        self.fired_at = fired_at
        self.reason = reason

    def to_dict(self) -> dict:
        return {
            "trigger_id": self.trigger_id,
            "model_name": self.model_name,
            "fired_at": self.fired_at,
            "reason": self.reason,
        }
