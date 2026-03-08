"""
Event schemas for Kafka-based event-driven architecture.

All domain events flow through Kafka. This module defines the event envelope
and domain-specific event payloads. Services produce and consume these events
to stay loosely coupled.

Event naming convention: <domain>.<entity>.<action>
  e.g., ride.trip.requested, driver.location.updated, payment.completed
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class Event(BaseModel):
    """
    Standard event envelope wrapping all domain events.

    Every event published to Kafka uses this envelope, ensuring consistent
    metadata (id, timestamp, source, correlation) across all 155 services.
    """
    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    event_type: str                    # e.g., "ride.trip.requested"
    source: str                        # Service that produced it
    timestamp: datetime = Field(default_factory=datetime.now)
    correlation_id: Optional[str] = None  # For distributed tracing
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_kafka_key(self) -> str:
        """Generate a Kafka partition key from the event."""
        # Default: use correlation_id or event_id for partitioning
        return self.correlation_id or str(self.event_id)


# ── Pre-defined event types ──
# These constants prevent typos and enable IDE autocomplete

class EventTypes:
    """Kafka topic / event type constants."""

    # Ride domain
    RIDE_REQUESTED = "ride.trip.requested"
    RIDE_DRIVER_ASSIGNED = "ride.trip.driver_assigned"
    RIDE_STARTED = "ride.trip.started"
    RIDE_COMPLETED = "ride.trip.completed"
    RIDE_CANCELLED = "ride.trip.cancelled"

    # Driver domain
    DRIVER_LOCATION_UPDATED = "driver.location.updated"
    DRIVER_WENT_ONLINE = "driver.status.online"
    DRIVER_WENT_OFFLINE = "driver.status.offline"

    # Payment domain
    PAYMENT_INITIATED = "payment.initiated"
    PAYMENT_COMPLETED = "payment.completed"
    PAYMENT_FAILED = "payment.failed"

    # Pricing domain
    SURGE_UPDATED = "pricing.surge.updated"

    # Platform domain
    USER_REGISTERED = "platform.user.registered"
    USER_VERIFIED = "platform.user.verified"
