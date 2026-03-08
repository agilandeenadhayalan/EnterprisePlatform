"""
Event Sourcing — State from Event History
==========================================

Instead of storing the current state of an entity, event sourcing stores
the sequence of events that led to that state. Current state is derived
by replaying all events from the beginning.

WHY event sourcing:
- Complete audit trail (every state change is recorded)
- Time travel (rebuild state at any point in history)
- No data loss (events are append-only, never deleted)
- Enables CQRS (separate read and write models)
- Debug by replaying events to understand what happened

TRADE-OFFS:
- More complex to implement
- Eventual consistency (read model may lag)
- Event schema evolution is tricky
- Snapshots needed for performance with many events
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TripEventType(str, Enum):
    TRIP_REQUESTED = "TripRequested"
    DRIVER_ASSIGNED = "DriverAssigned"
    TRIP_STARTED = "TripStarted"
    WAYPOINT_ADDED = "WaypointAdded"
    TRIP_COMPLETED = "TripCompleted"
    TRIP_CANCELLED = "TripCancelled"


@dataclass(frozen=True)
class TripEvent:
    """
    An immutable event representing a state change in a trip.

    Events are named in past tense — they represent facts that
    already happened and cannot be changed or deleted.
    """
    event_type: TripEventType
    trip_id: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    data: dict[str, Any] = field(default_factory=dict)
    version: int = 1


class TripStatus(str, Enum):
    REQUESTED = "requested"
    DRIVER_ASSIGNED = "driver_assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class TripState:
    """
    The current state of a trip — derived entirely from events.

    This is NOT stored directly. It's rebuilt by replaying events.
    Think of it as a materialized view of the event stream.
    """
    trip_id: str = ""
    rider_id: str = ""
    driver_id: str | None = None
    status: TripStatus = TripStatus.REQUESTED
    pickup_lat: float = 0.0
    pickup_lon: float = 0.0
    dropoff_lat: float = 0.0
    dropoff_lon: float = 0.0
    waypoints: list[tuple[float, float]] = field(default_factory=list)
    fare_amount: float | None = None
    cancellation_reason: str | None = None
    version: int = 0


class EventSourcedTrip:
    """
    Event-sourced trip aggregate.

    All state changes produce events. Current state is derived
    by applying events in order. No direct state mutation.

    Usage:
        trip = EventSourcedTrip()
        trip.request_trip("trip-1", "rider-1", 40.7484, -73.9857, 40.7580, -73.9855)
        trip.assign_driver("driver-42")
        trip.start_trip()
        trip.complete_trip(15.50)

        # Rebuild from events
        trip2 = EventSourcedTrip.from_events(trip.events)
        assert trip2.state == trip.state
    """

    def __init__(self) -> None:
        self._events: list[TripEvent] = []
        self._state = TripState()

    @property
    def state(self) -> TripState:
        return self._state

    @property
    def events(self) -> list[TripEvent]:
        return list(self._events)

    @property
    def version(self) -> int:
        return self._state.version

    # ── Command methods (produce events) ──

    def request_trip(
        self,
        trip_id: str,
        rider_id: str,
        pickup_lat: float,
        pickup_lon: float,
        dropoff_lat: float,
        dropoff_lon: float,
    ) -> None:
        """Request a new trip — produces TripRequested event."""
        self._apply(TripEvent(
            event_type=TripEventType.TRIP_REQUESTED,
            trip_id=trip_id,
            data={
                "rider_id": rider_id,
                "pickup_lat": pickup_lat,
                "pickup_lon": pickup_lon,
                "dropoff_lat": dropoff_lat,
                "dropoff_lon": dropoff_lon,
            },
        ))

    def assign_driver(self, driver_id: str) -> None:
        """Assign a driver — produces DriverAssigned event."""
        if self._state.status != TripStatus.REQUESTED:
            raise ValueError(f"Cannot assign driver in {self._state.status.value} state")
        self._apply(TripEvent(
            event_type=TripEventType.DRIVER_ASSIGNED,
            trip_id=self._state.trip_id,
            data={"driver_id": driver_id},
        ))

    def start_trip(self) -> None:
        """Start the trip — produces TripStarted event."""
        if self._state.status != TripStatus.DRIVER_ASSIGNED:
            raise ValueError(f"Cannot start trip in {self._state.status.value} state")
        self._apply(TripEvent(
            event_type=TripEventType.TRIP_STARTED,
            trip_id=self._state.trip_id,
        ))

    def add_waypoint(self, lat: float, lon: float) -> None:
        """Record a waypoint — produces WaypointAdded event."""
        if self._state.status != TripStatus.IN_PROGRESS:
            raise ValueError(f"Cannot add waypoint in {self._state.status.value} state")
        self._apply(TripEvent(
            event_type=TripEventType.WAYPOINT_ADDED,
            trip_id=self._state.trip_id,
            data={"lat": lat, "lon": lon},
        ))

    def complete_trip(self, fare_amount: float) -> None:
        """Complete the trip — produces TripCompleted event."""
        if self._state.status != TripStatus.IN_PROGRESS:
            raise ValueError(f"Cannot complete trip in {self._state.status.value} state")
        self._apply(TripEvent(
            event_type=TripEventType.TRIP_COMPLETED,
            trip_id=self._state.trip_id,
            data={"fare_amount": fare_amount},
        ))

    def cancel_trip(self, reason: str = "") -> None:
        """Cancel the trip — produces TripCancelled event."""
        if self._state.status in (TripStatus.COMPLETED, TripStatus.CANCELLED):
            raise ValueError(f"Cannot cancel trip in {self._state.status.value} state")
        self._apply(TripEvent(
            event_type=TripEventType.TRIP_CANCELLED,
            trip_id=self._state.trip_id,
            data={"reason": reason},
        ))

    # ── Event application (state derivation) ──

    def _apply(self, event: TripEvent) -> None:
        """Apply an event — update state and store the event."""
        self._apply_event(event)
        self._events.append(event)

    def _apply_event(self, event: TripEvent) -> None:
        """
        Pure state mutation from an event.

        This is the ONLY place where state changes happen.
        Each event type maps to a specific state change.
        """
        s = self._state

        if event.event_type == TripEventType.TRIP_REQUESTED:
            s.trip_id = event.trip_id
            s.rider_id = event.data["rider_id"]
            s.pickup_lat = event.data["pickup_lat"]
            s.pickup_lon = event.data["pickup_lon"]
            s.dropoff_lat = event.data["dropoff_lat"]
            s.dropoff_lon = event.data["dropoff_lon"]
            s.status = TripStatus.REQUESTED

        elif event.event_type == TripEventType.DRIVER_ASSIGNED:
            s.driver_id = event.data["driver_id"]
            s.status = TripStatus.DRIVER_ASSIGNED

        elif event.event_type == TripEventType.TRIP_STARTED:
            s.status = TripStatus.IN_PROGRESS

        elif event.event_type == TripEventType.WAYPOINT_ADDED:
            s.waypoints.append((event.data["lat"], event.data["lon"]))

        elif event.event_type == TripEventType.TRIP_COMPLETED:
            s.fare_amount = event.data["fare_amount"]
            s.status = TripStatus.COMPLETED

        elif event.event_type == TripEventType.TRIP_CANCELLED:
            s.cancellation_reason = event.data.get("reason", "")
            s.status = TripStatus.CANCELLED

        s.version += 1

    # ── Rebuild from events ──

    @classmethod
    def from_events(cls, events: list[TripEvent]) -> EventSourcedTrip:
        """
        Rebuild a trip aggregate from an event history.

        This is the core of event sourcing — the current state is
        derived entirely by replaying events in order.
        """
        trip = cls()
        for event in events:
            trip._apply_event(event)
            trip._events.append(event)
        return trip
