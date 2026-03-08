"""
Aggregates & Invariant Enforcement
====================================

Implements the TripAggregate — the central aggregate in a ride-hailing domain.

An Aggregate is a cluster of domain objects treated as a single unit for
data changes. The root entity (Trip) controls all access and enforces
business rules (invariants).

WHY aggregates:
- Consistency boundary: all changes within an aggregate are atomic
- Encapsulation: external code can't reach inside and break invariants
- Transaction boundary: one aggregate = one database transaction

State machine:
    REQUESTED --> DRIVER_ASSIGNED --> IN_PROGRESS --> COMPLETED
         |             |                  |
         v             v                  v
      CANCELLED     CANCELLED          (can't cancel)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TripStatus(str, Enum):
    REQUESTED = "requested"
    DRIVER_ASSIGNED = "driver_assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# ── Value Objects ──
# Immutable, compared by value (not identity)


@dataclass(frozen=True)
class Location:
    """GPS location value object — immutable, no identity."""
    lat: float
    lon: float
    address: str = ""

    def __post_init__(self) -> None:
        if not (-90 <= self.lat <= 90):
            raise ValueError(f"Invalid latitude: {self.lat}")
        if not (-180 <= self.lon <= 180):
            raise ValueError(f"Invalid longitude: {self.lon}")


@dataclass(frozen=True)
class Waypoint:
    """
    A point along the trip route — value object.

    Value objects have no identity. Two waypoints at the same location
    and time are considered equal, unlike entities which have unique IDs.
    """
    location: Location
    timestamp: datetime
    waypoint_type: str = "intermediate"  # "pickup", "dropoff", "intermediate"


@dataclass(frozen=True)
class FareBreakdown:
    """Immutable fare calculation result."""
    base_fare: float
    distance_charge: float
    time_charge: float
    surge_multiplier: float = 1.0
    tip: float = 0.0

    @property
    def total(self) -> float:
        subtotal = (self.base_fare + self.distance_charge + self.time_charge)
        return round(subtotal * self.surge_multiplier + self.tip, 2)


# ── Valid state transitions ──

_VALID_TRANSITIONS: dict[TripStatus, set[TripStatus]] = {
    TripStatus.REQUESTED: {TripStatus.DRIVER_ASSIGNED, TripStatus.CANCELLED},
    TripStatus.DRIVER_ASSIGNED: {TripStatus.IN_PROGRESS, TripStatus.CANCELLED},
    TripStatus.IN_PROGRESS: {TripStatus.COMPLETED},
    TripStatus.COMPLETED: set(),   # Terminal state
    TripStatus.CANCELLED: set(),   # Terminal state
}


# ── Trip Aggregate Root ──


class TripAggregate:
    """
    Trip Aggregate Root — the consistency boundary for a ride.

    All mutations go through this class. External code cannot directly
    modify waypoints, fare, or status. The aggregate enforces all
    business rules (invariants).

    INVARIANTS:
    1. A trip can't be completed without first being started (IN_PROGRESS)
    2. A trip can't be cancelled after completion
    3. A driver must be assigned before the trip starts
    4. Pickup and dropoff locations are required
    5. Fare can only be set when the trip is completed
    """

    def __init__(
        self,
        trip_id: str | None = None,
        rider_id: str = "",
        pickup: Location | None = None,
        dropoff: Location | None = None,
    ) -> None:
        self._trip_id = trip_id or str(uuid.uuid4())
        self._rider_id = rider_id
        self._driver_id: str | None = None
        self._status = TripStatus.REQUESTED
        self._pickup = pickup
        self._dropoff = dropoff
        self._waypoints: list[Waypoint] = []
        self._fare: FareBreakdown | None = None
        self._created_at = datetime.now()
        self._updated_at = datetime.now()
        self._cancellation_reason: str | None = None

        # Enforce: must have pickup and dropoff
        if pickup is None or dropoff is None:
            raise ValueError("Trip requires both pickup and dropoff locations")

    # ── Read-only properties (encapsulation) ──

    @property
    def trip_id(self) -> str:
        return self._trip_id

    @property
    def rider_id(self) -> str:
        return self._rider_id

    @property
    def driver_id(self) -> str | None:
        return self._driver_id

    @property
    def status(self) -> TripStatus:
        return self._status

    @property
    def pickup(self) -> Location:
        assert self._pickup is not None
        return self._pickup

    @property
    def dropoff(self) -> Location:
        assert self._dropoff is not None
        return self._dropoff

    @property
    def waypoints(self) -> tuple[Waypoint, ...]:
        return tuple(self._waypoints)

    @property
    def fare(self) -> FareBreakdown | None:
        return self._fare

    @property
    def cancellation_reason(self) -> str | None:
        return self._cancellation_reason

    # ── State transitions (command methods) ──

    def _transition_to(self, new_status: TripStatus) -> None:
        """Enforce valid state transitions."""
        valid = _VALID_TRANSITIONS.get(self._status, set())
        if new_status not in valid:
            raise InvalidTransitionError(
                f"Cannot transition from {self._status.value} to {new_status.value}. "
                f"Valid transitions: {[s.value for s in valid]}"
            )
        self._status = new_status
        self._updated_at = datetime.now()

    def assign_driver(self, driver_id: str) -> None:
        """
        Assign a driver to this trip.

        INVARIANT: Can only assign a driver to a REQUESTED trip.
        """
        if not driver_id:
            raise ValueError("Driver ID cannot be empty")
        self._transition_to(TripStatus.DRIVER_ASSIGNED)
        self._driver_id = driver_id

    def start_trip(self) -> None:
        """
        Start the trip (driver picked up rider).

        INVARIANT: A driver must be assigned before starting.
        INVARIANT: Cannot start a completed or cancelled trip.
        """
        self._transition_to(TripStatus.IN_PROGRESS)
        # Record pickup waypoint
        self._waypoints.append(Waypoint(
            location=self.pickup,
            timestamp=datetime.now(),
            waypoint_type="pickup",
        ))

    def add_waypoint(self, location: Location) -> None:
        """
        Record an intermediate waypoint during the trip.

        INVARIANT: Can only add waypoints during IN_PROGRESS.
        """
        if self._status != TripStatus.IN_PROGRESS:
            raise InvalidStateError(
                f"Cannot add waypoints in {self._status.value} state"
            )
        self._waypoints.append(Waypoint(
            location=location,
            timestamp=datetime.now(),
            waypoint_type="intermediate",
        ))

    def complete_trip(self, fare: FareBreakdown) -> None:
        """
        Complete the trip with a fare breakdown.

        INVARIANT: Can only complete an IN_PROGRESS trip.
        INVARIANT: Fare must have a positive total.
        """
        if fare.total <= 0:
            raise ValueError(f"Fare total must be positive, got {fare.total}")

        self._transition_to(TripStatus.COMPLETED)
        self._fare = fare
        # Record dropoff waypoint
        self._waypoints.append(Waypoint(
            location=self.dropoff,
            timestamp=datetime.now(),
            waypoint_type="dropoff",
        ))

    def cancel_trip(self, reason: str = "") -> None:
        """
        Cancel the trip.

        INVARIANT: Cannot cancel a completed trip.
        INVARIANT: Cannot cancel an already cancelled trip.
        """
        self._transition_to(TripStatus.CANCELLED)
        self._cancellation_reason = reason or "No reason provided"

    def to_dict(self) -> dict[str, Any]:
        """Serialize aggregate state for display/storage."""
        return {
            "trip_id": self._trip_id,
            "rider_id": self._rider_id,
            "driver_id": self._driver_id,
            "status": self._status.value,
            "pickup": f"({self.pickup.lat}, {self.pickup.lon})",
            "dropoff": f"({self.dropoff.lat}, {self.dropoff.lon})",
            "waypoint_count": len(self._waypoints),
            "fare": self._fare.total if self._fare else None,
            "cancellation_reason": self._cancellation_reason,
        }


# ── Domain Exceptions ──


class InvalidTransitionError(Exception):
    """Raised when attempting an invalid state transition."""
    pass


class InvalidStateError(Exception):
    """Raised when attempting an operation in the wrong state."""
    pass
