"""
Domain models for the city simulator.

Agent-based city simulation with drivers, riders, and vehicles.
"""

import random
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class AgentType(str, Enum):
    """Types of simulation agents."""
    DRIVER = "driver"
    RIDER = "rider"
    VEHICLE = "vehicle"


class SimulationStatus(str, Enum):
    """Status of a simulation run."""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    STOPPED = "stopped"


class SimulationRun:
    """A simulation run instance."""

    def __init__(
        self,
        id: str,
        simulation_type: str = "city",
        scenario: Optional[dict[str, Any]] = None,
        status: str = "created",
        num_agents: int = 0,
        num_ticks: int = 0,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
    ):
        self.id = id
        self.simulation_type = simulation_type
        self.scenario = scenario or {}
        self.status = status
        self.num_agents = num_agents
        self.num_ticks = num_ticks
        self.started_at = started_at or datetime.utcnow()
        self.completed_at = completed_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "simulation_type": self.simulation_type,
            "scenario": self.scenario,
            "status": self.status,
            "num_agents": self.num_agents,
            "num_ticks": self.num_ticks,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class SimAgent:
    """A simulation agent (driver, rider, or vehicle)."""

    def __init__(
        self,
        id: str,
        run_id: str,
        agent_type: str = "driver",
        state: Optional[dict[str, Any]] = None,
        position: Optional[dict[str, float]] = None,
    ):
        self.id = id
        self.run_id = run_id
        self.agent_type = agent_type
        self.state = state or {"status": "idle"}
        self.position = position or {"lat": 40.7128 + random.uniform(-0.05, 0.05), "lon": -74.0060 + random.uniform(-0.05, 0.05)}

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "agent_type": self.agent_type,
            "state": self.state,
            "position": self.position,
        }


class SimulationMetrics:
    """Simulation metrics/KPIs."""

    def __init__(
        self,
        total_trips: int = 0,
        avg_wait_time: float = 0.0,
        avg_trip_time: float = 0.0,
        utilization: float = 0.0,
        supply_demand_ratio: float = 1.0,
    ):
        self.total_trips = total_trips
        self.avg_wait_time = avg_wait_time
        self.avg_trip_time = avg_trip_time
        self.utilization = utilization
        self.supply_demand_ratio = supply_demand_ratio

    def to_dict(self) -> dict:
        return {
            "total_trips": self.total_trips,
            "avg_wait_time": round(self.avg_wait_time, 2),
            "avg_trip_time": round(self.avg_trip_time, 2),
            "utilization": round(self.utilization, 4),
            "supply_demand_ratio": round(self.supply_demand_ratio, 4),
        }
