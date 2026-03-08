"""
Kafka topic name constants.

Centralizing topic names prevents typos and enables IDE autocomplete.
Topic naming convention: <domain>.<entity>.<version>
"""


class Topics:
    """Kafka topic constants for all domain events."""

    # ── Ride Domain ──
    RIDE_EVENTS = "ride.events.v1"
    RIDE_REQUESTS = "ride.requests.v1"
    RIDE_STATUS = "ride.status.v1"
    RIDE_TRACKING = "ride.tracking.v1"

    # ── Driver Domain ──
    DRIVER_EVENTS = "driver.events.v1"
    DRIVER_LOCATION = "driver.location.v1"
    DRIVER_STATUS = "driver.status.v1"
    DRIVER_MATCHING = "driver.matching.v1"

    # ── Payment Domain ──
    PAYMENT_EVENTS = "payment.events.v1"
    PAYMENT_PAYOUT = "payment.payout.v1"

    # ── Pricing Domain ──
    PRICING_EVENTS = "pricing.events.v1"
    SURGE_UPDATES = "pricing.surge.v1"

    # ── Dispatch Domain ──
    DISPATCH_EVENTS = "dispatch.events.v1"
    DISPATCH_ASSIGNMENTS = "dispatch.assignments.v1"

    # ── Communication Domain ──
    NOTIFICATION_EVENTS = "notification.events.v1"
    CHAT_MESSAGES = "chat.messages.v1"

    # ── Platform Domain ──
    PLATFORM_EVENTS = "platform.events.v1"
    AUDIT_TRAIL = "platform.audit.v1"

    # ── Dead Letter Queues ──
    DLQ_PREFIX = "dlq."

    @classmethod
    def dlq_for(cls, topic: str) -> str:
        """Get the dead letter queue topic for a given topic."""
        return f"{cls.DLQ_PREFIX}{topic}"
