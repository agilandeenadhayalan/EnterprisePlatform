"""
Pydantic request/response schemas for the city simulator API.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Request schemas ──

class RunCreate(BaseModel):
    """POST /simulation/city/runs — create/start simulation run."""
    simulation_type: str = Field(default="city", description="Simulation type")
    scenario: Optional[dict[str, Any]] = Field(default=None, description="Scenario configuration")
    num_agents: int = Field(default=0, description="Initial number of agents")


class RunUpdate(BaseModel):
    """PATCH /simulation/city/runs/{id} — update run (pause/resume/stop)."""
    status: Optional[str] = None


class AgentAdd(BaseModel):
    """POST /simulation/city/runs/{id}/agents — add agents."""
    agent_type: str = Field(default="driver", description="Agent type: driver, rider, vehicle")
    count: int = Field(default=1, description="Number of agents to add")


# ── Response schemas ──

class RunResponse(BaseModel):
    """A simulation run."""
    id: str
    simulation_type: str
    scenario: dict[str, Any] = {}
    status: str
    num_agents: int
    num_ticks: int
    started_at: datetime
    completed_at: Optional[datetime] = None


class AgentResponse(BaseModel):
    """A simulation agent."""
    id: str
    run_id: str
    agent_type: str
    state: dict[str, Any] = {}
    position: dict[str, float] = {}


class MetricsResponse(BaseModel):
    """Simulation metrics/KPIs."""
    total_trips: int
    avg_wait_time: float
    avg_trip_time: float
    utilization: float
    supply_demand_ratio: float


class StepResponse(BaseModel):
    """Result of a simulation step."""
    tick: int
    agents_moved: int
    trips_completed: int
    status: str
