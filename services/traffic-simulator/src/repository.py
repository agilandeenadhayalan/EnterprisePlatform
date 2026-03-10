"""
Traffic Simulator repository — in-memory traffic simulation state.

Manages traffic runs, road segments, incidents, and congestion modeling.
"""

import random
import uuid
from datetime import datetime
from typing import Any, Optional

from models import TrafficRun, RoadSegment, TrafficIncident, CongestionLevel


ROAD_NAMES = [
    "Main Street", "Broadway", "5th Avenue", "Highway 101",
    "Interstate 95", "Park Avenue", "Market Street", "Oak Boulevard",
    "Elm Drive", "River Road",
]


def _compute_congestion(speed_ratio: float) -> str:
    """Determine congestion level from speed ratio (current/limit)."""
    if speed_ratio >= 0.9:
        return "free_flow"
    elif speed_ratio >= 0.7:
        return "light"
    elif speed_ratio >= 0.5:
        return "moderate"
    elif speed_ratio >= 0.25:
        return "heavy"
    else:
        return "gridlock"


class TrafficSimulatorRepository:
    """In-memory traffic simulation storage."""

    def __init__(self):
        self._runs: dict[str, TrafficRun] = {}
        self._segments: dict[str, list[RoadSegment]] = {}  # run_id -> segments
        self._incidents: dict[str, list[TrafficIncident]] = {}  # run_id -> incidents

    # ── Runs ──

    def create_run(
        self,
        num_segments: int = 5,
        config: Optional[dict[str, Any]] = None,
    ) -> TrafficRun:
        """Start a traffic simulation run."""
        run_id = str(uuid.uuid4())
        run = TrafficRun(
            id=run_id,
            status="created",
            num_segments=num_segments,
            config=config,
        )
        self._runs[run_id] = run
        self._incidents[run_id] = []

        # Create road segments
        segments = []
        for i in range(num_segments):
            name = ROAD_NAMES[i % len(ROAD_NAMES)]
            speed_limit = random.choice([30.0, 45.0, 60.0, 80.0, 100.0])
            segment = RoadSegment(
                id=str(uuid.uuid4()),
                run_id=run_id,
                name=name,
                speed_limit=speed_limit,
                current_speed=speed_limit,
                congestion_level="free_flow",
                vehicles_count=random.randint(5, 20),
            )
            segments.append(segment)
        self._segments[run_id] = segments
        return run

    def list_runs(self) -> list[TrafficRun]:
        """List all runs."""
        return list(self._runs.values())

    def get_run(self, run_id: str) -> Optional[TrafficRun]:
        """Get a run by ID."""
        return self._runs.get(run_id)

    # ── Step ──

    def step(self, run_id: str) -> Optional[dict]:
        """Step traffic simulation."""
        run = self._runs.get(run_id)
        if not run:
            return None
        if run.status not in ("created", "running"):
            return None

        run.status = "running"
        run.num_ticks += 1

        segments = self._segments.get(run_id, [])
        total_vehicles = 0
        total_speed = 0.0

        for segment in segments:
            # Randomly adjust vehicles
            segment.vehicles_count += random.randint(-3, 5)
            segment.vehicles_count = max(0, segment.vehicles_count)
            total_vehicles += segment.vehicles_count

            # Speed affected by vehicle count
            load_factor = max(0.1, 1.0 - (segment.vehicles_count / 100.0))
            segment.current_speed = round(segment.speed_limit * load_factor, 2)

            # Check for active incidents
            active_incidents = [
                inc for inc in self._incidents.get(run_id, [])
                if inc.segment_id == segment.id and inc.resolved_at is None
            ]
            for inc in active_incidents:
                segment.current_speed *= max(0.1, 1.0 - inc.severity * 0.15)
                segment.current_speed = round(segment.current_speed, 2)

            speed_ratio = segment.current_speed / segment.speed_limit if segment.speed_limit > 0 else 1.0
            segment.congestion_level = _compute_congestion(speed_ratio)
            total_speed += segment.current_speed

        avg_speed = round(total_speed / len(segments), 2) if segments else 0.0

        return {
            "tick": run.num_ticks,
            "segments_updated": len(segments),
            "total_vehicles": total_vehicles,
            "avg_speed": avg_speed,
            "status": run.status,
        }

    # ── Congestion ──

    def get_congestion(self, run_id: str) -> Optional[list[dict]]:
        """Get congestion map."""
        segments = self._segments.get(run_id)
        if segments is None:
            return None
        return [
            {
                "segment_id": s.id,
                "segment_name": s.name,
                "congestion_level": s.congestion_level,
                "current_speed": s.current_speed,
                "speed_limit": s.speed_limit,
                "vehicles_count": s.vehicles_count,
            }
            for s in segments
        ]

    # ── Incidents ──

    def inject_incident(
        self,
        run_id: str,
        segment_id: str,
        incident_type: str = "accident",
        severity: int = 1,
        impact_radius: float = 1.0,
    ) -> Optional[TrafficIncident]:
        """Inject a traffic incident."""
        if run_id not in self._runs:
            return None
        # Validate segment exists
        segments = self._segments.get(run_id, [])
        if not any(s.id == segment_id for s in segments):
            return None
        incident = TrafficIncident(
            id=str(uuid.uuid4()),
            run_id=run_id,
            segment_id=segment_id,
            incident_type=incident_type,
            severity=min(severity, 5),
            impact_radius=impact_radius,
        )
        self._incidents[run_id].append(incident)
        return incident

    # ── Route conditions ──

    def get_route_conditions(self, run_id: str) -> Optional[list[dict]]:
        """Get route conditions."""
        segments = self._segments.get(run_id)
        if segments is None:
            return None
        return [
            {
                "segment_id": s.id,
                "segment_name": s.name,
                "travel_time_factor": round(s.speed_limit / max(1.0, s.current_speed), 2),
                "congestion_level": s.congestion_level,
            }
            for s in segments
        ]


# Singleton repository instance
repo = TrafficSimulatorRepository()
