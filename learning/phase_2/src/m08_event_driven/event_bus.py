"""
Event Bus — Publish/Subscribe Pattern
=======================================

In-memory event bus that demonstrates the core messaging patterns used
in event-driven architectures (Kafka, RabbitMQ, NATS).

WHY event bus over direct calls:
- Decoupling: publishers don't know about subscribers
- Extensibility: add new subscribers without modifying publishers
- Resilience: failures in one subscriber don't affect others
- Replay: event store enables rebuilding state from history

Architecture:
    Publisher --> EventBus --> [Handler 1]
                          --> [Handler 2]
                          --> [Handler N]
                          --> EventStore (append-only log)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable


@dataclass(frozen=True)
class DomainEvent:
    """
    Base domain event — immutable record of something that happened.

    Events are named in past tense (TripRequested, not RequestTrip)
    because they represent facts that already occurred.
    """
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ""
    aggregate_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    data: dict[str, Any] = field(default_factory=dict)
    version: int = 1


# Type alias for event handlers
EventHandler = Callable[[DomainEvent], None]


class EventBus:
    """
    In-memory event bus with topic-based publish/subscribe.

    Supports:
    - Sync handlers (called immediately on publish)
    - Event store (append-only log for replay)
    - Topic-based routing (subscribe to specific event types)
    - Wildcard subscriptions (receive all events)
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = {}
        self._event_store: list[DomainEvent] = []
        self._dead_letter: list[tuple[DomainEvent, str]] = []

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """
        Subscribe a handler to a specific event type.

        Use "*" to subscribe to all event types.
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Remove a handler from a specific event type."""
        if event_type in self._handlers:
            self._handlers[event_type] = [
                h for h in self._handlers[event_type] if h is not handler
            ]

    def publish(self, event: DomainEvent) -> list[str]:
        """
        Publish an event to all registered handlers.

        Returns a list of any errors from handlers (handlers that fail
        don't prevent other handlers from being called).
        """
        self._event_store.append(event)
        errors: list[str] = []

        # Get handlers for this specific event type
        handlers = list(self._handlers.get(event.event_type, []))
        # Add wildcard handlers
        handlers.extend(self._handlers.get("*", []))

        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                error_msg = f"Handler {handler.__name__} failed: {e}"
                errors.append(error_msg)
                self._dead_letter.append((event, error_msg))

        return errors

    def replay(
        self,
        aggregate_id: str | None = None,
        event_type: str | None = None,
        handler: EventHandler | None = None,
    ) -> list[DomainEvent]:
        """
        Replay events from the event store.

        If a handler is provided, each matching event is passed to it.
        Returns the list of matching events.

        WHY replay: Rebuild read models, recover state after crashes,
        create new projections from historical data.
        """
        events = self._event_store

        if aggregate_id:
            events = [e for e in events if e.aggregate_id == aggregate_id]
        if event_type:
            events = [e for e in events if e.event_type == event_type]

        if handler:
            for event in events:
                handler(event)

        return list(events)

    @property
    def event_store(self) -> list[DomainEvent]:
        """Read-only access to the event store."""
        return list(self._event_store)

    @property
    def dead_letter_queue(self) -> list[tuple[DomainEvent, str]]:
        """Events that failed processing."""
        return list(self._dead_letter)

    def clear(self) -> None:
        """Clear all handlers and events (for testing)."""
        self._handlers.clear()
        self._event_store.clear()
        self._dead_letter.clear()
