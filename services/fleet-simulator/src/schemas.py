"""
Pydantic request/response schemas for the fleet simulator API.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Request schemas ──

class FleetRunCreate(BaseModel):
    """POST /simulation/fleet/runs — start fleet simulation."""
    num_drivers: int = Field(default=10, description="Number of drivers")
    config: Optional[dict[str, Any]] = Field(default=None, description="Simulation config")


class DemandInject(BaseModel):
    """POST /simulation/fleet/runs/{id}/demand — inject demand event."""
    pickup: Optional[dict[str, float]] = Field(default=None, description="Pickup location")
    dropoff: Optional[dict[str, float]] = Field(default=None, description="Dropoff location")


# ── Response schemas ──

class FleetRunResponse(BaseModel):
    """A fleet simulation run."""
    id: str
    status: str
    num_drivers: int
    num_ticks: int
    config: dict[str, Any] = {}
    created_at: datetime


class DriverResponse(BaseModel):
    """A simulated driver."""
    id: str
    run_id: str
    state: str
    position: dict[str, float]
    current_trip_id: Optional[str] = None


class DemandEventResponse(BaseModel):
    """A demand event."""
    id: str
    run_id: str
    pickup: dict[str, float]
    dropoff: dict[str, float]
    timestamp: datetime


class StepResponse(BaseModel):
    """Result of a simulation step."""
    tick: int
    drivers_moved: int
    trips_started: int
    trips_completed: int
    status: str


class SupplyDemandResponse(BaseModel):
    """Supply/demand analytics."""
    idle_drivers: int
    active_drivers: int
    pending_requests: int
    utilization_rate: float
