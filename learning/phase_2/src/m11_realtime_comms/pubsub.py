"""
Pub/Sub System with Topic-Based Routing
=========================================

In-memory publish/subscribe system supporting channels, subscribers,
message ordering guarantees, and topic-based routing.

WHY pub/sub for real-time:
- Decouples message producers from consumers
- Supports one-to-many broadcasting (driver location to all watchers)
- Topic-based routing allows fine-grained subscriptions
- Message ordering ensures state consistency

Topic patterns:
    "trip.123.location"   — Location updates for trip 123
    "trip.123.*"          — All events for trip 123
    "trip.*.location"     — All location updates
    "driver.456.status"   — Status changes for driver 456
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class Message:
    """An immutable message in the pub/sub system."""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    topic: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    sequence: int = 0


# Type alias for message handlers
MessageHandler = Callable[[Message], None]


class Channel:
    """
    A named channel that subscribers can join.

    Channels maintain message ordering and track delivery.
    Each channel has its own message sequence counter.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self._subscribers: list[tuple[str, MessageHandler]] = []
        self._message_log: list[Message] = []
        self._sequence = 0

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)

    @property
    def message_count(self) -> int:
        return len(self._message_log)

    @property
    def messages(self) -> list[Message]:
        return list(self._message_log)

    def subscribe(self, subscriber_id: str, handler: MessageHandler) -> None:
        """Add a subscriber to this channel."""
        # Prevent duplicate subscriptions
        for sid, _ in self._subscribers:
            if sid == subscriber_id:
                return
        self._subscribers.append((subscriber_id, handler))

    def unsubscribe(self, subscriber_id: str) -> None:
        """Remove a subscriber from this channel."""
        self._subscribers = [
            (sid, h) for sid, h in self._subscribers if sid != subscriber_id
        ]

    def publish(self, payload: dict[str, Any], topic: str = "") -> Message:
        """Publish a message to all subscribers with ordering guarantee."""
        self._sequence += 1
        msg = Message(
            topic=topic or self.name,
            payload=payload,
            sequence=self._sequence,
        )
        self._message_log.append(msg)

        for subscriber_id, handler in self._subscribers:
            try:
                handler(msg)
            except Exception:
                pass  # In production: dead letter queue

        return msg


def _topic_matches(pattern: str, topic: str) -> bool:
    """
    Check if a topic matches a pattern with wildcard support.

    '*' matches a single segment, '#' matches one or more segments.
    Example: "trip.*.location" matches "trip.123.location"
             "trip.123.#" matches "trip.123.location" and "trip.123.a.b"
    """
    pattern_parts = pattern.split(".")
    topic_parts = topic.split(".")

    # Check for '#' wildcard anywhere in pattern
    for i, p in enumerate(pattern_parts):
        if p == "#":
            # '#' matches one or more remaining segments
            # Everything before '#' must match exactly (or via '*')
            prefix = pattern_parts[:i]
            if len(topic_parts) < len(prefix):
                return False
            for pp, tp in zip(prefix, topic_parts):
                if pp != "*" and pp != tp:
                    return False
            return len(topic_parts) >= len(prefix) + 1  # '#' must match at least 1

    if len(pattern_parts) != len(topic_parts):
        return False

    for p, t in zip(pattern_parts, topic_parts):
        if p == "*":
            continue  # Wildcard matches anything
        if p != t:
            return False
    return True


class PubSubSystem:
    """
    Topic-based pub/sub system with wildcard subscriptions.

    Supports:
    - Exact topic matching ("trip.123.location")
    - Single-level wildcards ("trip.*.location")
    - Multi-level wildcards ("trip.123.#")
    - Channel-based grouping
    - Message replay from history
    """

    def __init__(self) -> None:
        self._channels: dict[str, Channel] = {}
        self._topic_handlers: dict[str, list[tuple[str, MessageHandler]]] = defaultdict(list)
        self._global_log: list[Message] = []
        self._sequence = 0

    def create_channel(self, name: str) -> Channel:
        """Create or get a named channel."""
        if name not in self._channels:
            self._channels[name] = Channel(name)
        return self._channels[name]

    def get_channel(self, name: str) -> Channel | None:
        """Get a channel by name."""
        return self._channels.get(name)

    def subscribe(
        self,
        topic_pattern: str,
        subscriber_id: str,
        handler: MessageHandler,
    ) -> None:
        """Subscribe to a topic pattern (supports wildcards)."""
        self._topic_handlers[topic_pattern].append((subscriber_id, handler))

    def unsubscribe(self, topic_pattern: str, subscriber_id: str) -> None:
        """Unsubscribe from a topic pattern."""
        if topic_pattern in self._topic_handlers:
            self._topic_handlers[topic_pattern] = [
                (sid, h) for sid, h in self._topic_handlers[topic_pattern]
                if sid != subscriber_id
            ]

    def publish(self, topic: str, payload: dict[str, Any]) -> Message:
        """Publish a message to a topic, delivering to all matching subscribers."""
        self._sequence += 1
        msg = Message(
            topic=topic,
            payload=payload,
            sequence=self._sequence,
        )
        self._global_log.append(msg)

        # Find all matching handlers
        delivered_to: set[str] = set()
        for pattern, handlers in self._topic_handlers.items():
            if _topic_matches(pattern, topic):
                for subscriber_id, handler in handlers:
                    if subscriber_id not in delivered_to:
                        try:
                            handler(msg)
                            delivered_to.add(subscriber_id)
                        except Exception:
                            pass

        return msg

    def replay(
        self,
        topic_pattern: str | None = None,
        since_sequence: int = 0,
    ) -> list[Message]:
        """Replay messages from history, optionally filtered by topic."""
        messages = [m for m in self._global_log if m.sequence > since_sequence]

        if topic_pattern:
            messages = [m for m in messages if _topic_matches(topic_pattern, m.topic)]

        return messages

    @property
    def total_messages(self) -> int:
        return len(self._global_log)
