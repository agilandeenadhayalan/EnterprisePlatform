"""
Pydantic request/response schemas for the traffic simulator API.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Request schemas ──

class TrafficRunCreate(BaseModel):
    """POST /simulation/traffic/runs — start traffic simulation."""
    num_segments: int = Field(default=5, description="Number of road segments")
    config: Optional[dict[str, Any]] = Field(default=None, description="Simulation config")


class IncidentInject(BaseModel):
    """POST /simulation/traffic/runs/{id}/incident — inject traffic incident."""
    segment_id: str = Field(..., description="Road segment ID")
    incident_type: str = Field(default="accident", description="Incident type")
    severity: int = Field(default=1, description="Severity 1-5")
    impact_radius: float = Field(default=1.0, description="Impact radius in km")


# ── Response schemas ──

class TrafficRunResponse(BaseModel):
    """A traffic simulation run."""
    id: str
    status: str
    num_segments: int
    num_ticks: int
    config: dict[str, Any] = {}
    created_at: datetime


class RoadSegmentResponse(BaseModel):
    """A road segment."""
    id: str
    run_id: str
    name: str
    speed_limit: float
    current_speed: float
    congestion_level: str
    vehicles_count: int


class IncidentResponse(BaseModel):
    """A traffic incident."""
    id: str
    run_id: str
    segment_id: str
    incident_type: str
    severity: int
    impact_radius: float
    started_at: datetime
    resolved_at: Optional[datetime] = None


class StepResponse(BaseModel):
    """Result of a simulation step."""
    tick: int
    segments_updated: int
    total_vehicles: int
    avg_speed: float
    status: str


class CongestionMapEntry(BaseModel):
    """Congestion info for a segment."""
    segment_id: str
    segment_name: str
    congestion_level: str
    current_speed: float
    speed_limit: float
    vehicles_count: int


class RouteConditionResponse(BaseModel):
    """Route conditions for a segment."""
    segment_id: str
    segment_name: str
    travel_time_factor: float
    congestion_level: str
