"""
Domain models for the fleet simulator.

Fleet behavior simulation with driver state transitions and demand events.
"""

import random
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class DriverState(str, Enum):
    """Driver operational states."""
    IDLE = "idle"
    EN_ROUTE_PICKUP = "en_route_pickup"
    ON_TRIP = "on_trip"
    OFFLINE = "offline"


class SimulationStatus(str, Enum):
    """Status of a simulation run."""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    STOPPED = "stopped"


class FleetRun:
    """A fleet simulation run."""

    def __init__(
        self,
        id: str,
        status: str = "created",
        num_drivers: int = 0,
        num_ticks: int = 0,
        config: Optional[dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
    ):
        self.id = id
        self.status = status
        self.num_drivers = num_drivers
        self.num_ticks = num_ticks
        self.config = config or {}
        self.created_at = created_at or datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "status": self.status,
            "num_drivers": self.num_drivers,
            "num_ticks": self.num_ticks,
            "config": self.config,
            "created_at": self.created_at.isoformat(),
        }


class SimDriver:
    """A simulated driver."""

    def __init__(
        self,
        id: str,
        run_id: str,
        state: str = "idle",
        position: Optional[dict[str, float]] = None,
        current_trip_id: Optional[str] = None,
    ):
        self.id = id
        self.run_id = run_id
        self.state = state
        self.position = position or {
            "lat": 40.7128 + random.uniform(-0.05, 0.05),
            "lon": -74.0060 + random.uniform(-0.05, 0.05),
        }
        self.current_trip_id = current_trip_id

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "state": self.state,
            "position": self.position,
            "current_trip_id": self.current_trip_id,
        }


class DemandEvent:
    """A demand event (ride request)."""

    def __init__(
        self,
        id: str,
        run_id: str,
        pickup: Optional[dict[str, float]] = None,
        dropoff: Optional[dict[str, float]] = None,
        timestamp: Optional[datetime] = None,
    ):
        self.id = id
        self.run_id = run_id
        self.pickup = pickup or {"lat": 40.7128, "lon": -74.0060}
        self.dropoff = dropoff or {"lat": 40.7580, "lon": -73.9855}
        self.timestamp = timestamp or datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "pickup": self.pickup,
            "dropoff": self.dropoff,
            "timestamp": self.timestamp.isoformat(),
        }
