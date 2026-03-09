"""
Domain models for the test data generator service.

Represents generator configuration, status, event templates, and generated events.
"""

from datetime import datetime
from typing import Any, Optional


class GeneratorConfig:
    """Configuration for event generation."""

    def __init__(
        self,
        mode: str,
        events_per_second: int,
        duration_seconds: int,
    ):
        self.mode = mode  # replay, synthetic, stress
        self.events_per_second = events_per_second
        self.duration_seconds = duration_seconds

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "events_per_second": self.events_per_second,
            "duration_seconds": self.duration_seconds,
        }


class GeneratorStatus:
    """Current state of the generator."""

    def __init__(
        self,
        is_running: bool,
        mode: Optional[str] = None,
        events_generated: int = 0,
        events_per_second: int = 0,
        elapsed_seconds: float = 0.0,
        started_at: Optional[str] = None,
    ):
        self.is_running = is_running
        self.mode = mode
        self.events_generated = events_generated
        self.events_per_second = events_per_second
        self.elapsed_seconds = elapsed_seconds
        self.started_at = started_at

    def to_dict(self) -> dict:
        return {
            "is_running": self.is_running,
            "mode": self.mode,
            "events_generated": self.events_generated,
            "events_per_second": self.events_per_second,
            "elapsed_seconds": self.elapsed_seconds,
            "started_at": self.started_at,
        }


class EventTemplate:
    """Template definition for a type of event."""

    def __init__(
        self,
        template_id: str,
        name: str,
        description: str,
        event_type: str,
        fields: list[dict[str, str]],
        sample: dict[str, Any],
    ):
        self.template_id = template_id
        self.name = name
        self.description = description
        self.event_type = event_type
        self.fields = fields
        self.sample = sample

    def to_dict(self) -> dict:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "event_type": self.event_type,
            "fields": self.fields,
            "sample": self.sample,
        }


class GeneratedEvent:
    """A single generated event."""

    def __init__(
        self,
        event_id: str,
        event_type: str,
        timestamp: str,
        data: dict[str, Any],
    ):
        self.event_id = event_id
        self.event_type = event_type
        self.timestamp = timestamp
        self.data = data

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "data": self.data,
        }
