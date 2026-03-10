"""
Domain models for the traffic simulator.

Traffic patterns, congestion modeling, and road segment management.
"""

import random
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class CongestionLevel(str, Enum):
    """Traffic congestion levels."""
    FREE_FLOW = "free_flow"
    LIGHT = "light"
    MODERATE = "moderate"
    HEAVY = "heavy"
    GRIDLOCK = "gridlock"


class SimulationStatus(str, Enum):
    """Status of a simulation run."""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    STOPPED = "stopped"


class TrafficRun:
    """A traffic simulation run."""

    def __init__(
        self,
        id: str,
        status: str = "created",
        num_segments: int = 0,
        num_ticks: int = 0,
        config: Optional[dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
    ):
        self.id = id
        self.status = status
        self.num_segments = num_segments
        self.num_ticks = num_ticks
        self.config = config or {}
        self.created_at = created_at or datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "status": self.status,
            "num_segments": self.num_segments,
            "num_ticks": self.num_ticks,
            "config": self.config,
            "created_at": self.created_at.isoformat(),
        }


class RoadSegment:
    """A road segment in the simulation."""

    def __init__(
        self,
        id: str,
        run_id: str,
        name: str,
        speed_limit: float = 60.0,
        current_speed: float = 60.0,
        congestion_level: str = "free_flow",
        vehicles_count: int = 0,
    ):
        self.id = id
        self.run_id = run_id
        self.name = name
        self.speed_limit = speed_limit
        self.current_speed = current_speed
        self.congestion_level = congestion_level
        self.vehicles_count = vehicles_count

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "name": self.name,
            "speed_limit": self.speed_limit,
            "current_speed": round(self.current_speed, 2),
            "congestion_level": self.congestion_level,
            "vehicles_count": self.vehicles_count,
        }


class TrafficIncident:
    """A traffic incident."""

    def __init__(
        self,
        id: str,
        run_id: str,
        segment_id: str,
        incident_type: str = "accident",
        severity: int = 1,
        impact_radius: float = 1.0,
        started_at: Optional[datetime] = None,
        resolved_at: Optional[datetime] = None,
    ):
        self.id = id
        self.run_id = run_id
        self.segment_id = segment_id
        self.incident_type = incident_type
        self.severity = severity
        self.impact_radius = impact_radius
        self.started_at = started_at or datetime.utcnow()
        self.resolved_at = resolved_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "segment_id": self.segment_id,
            "incident_type": self.incident_type,
            "severity": self.severity,
            "impact_radius": self.impact_radius,
            "started_at": self.started_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }
