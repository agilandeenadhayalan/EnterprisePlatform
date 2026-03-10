"""
Domain models for the load test service.

Manages load test scenarios, runs, and results with latency analysis.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional


class LoadPattern(str, Enum):
    """Load test patterns."""
    RAMP = "ramp"
    SPIKE = "spike"
    SOAK = "soak"
    STRESS = "stress"


class RunStatus(str, Enum):
    """Status of a test run."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TestScenario:
    """A load test scenario definition."""

    def __init__(
        self,
        id: str,
        name: str,
        pattern: str = "ramp",
        target_rps: int = 100,
        duration_seconds: int = 60,
        config: Optional[dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
    ):
        self.id = id
        self.name = name
        self.pattern = pattern
        self.target_rps = target_rps
        self.duration_seconds = duration_seconds
        self.config = config or {}
        self.created_at = created_at or datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "pattern": self.pattern,
            "target_rps": self.target_rps,
            "duration_seconds": self.duration_seconds,
            "config": self.config,
            "created_at": self.created_at.isoformat(),
        }


class TestResult:
    """Results from a load test run."""

    def __init__(
        self,
        id: str,
        run_id: str,
        p50_ms: float = 0.0,
        p95_ms: float = 0.0,
        p99_ms: float = 0.0,
        error_rate: float = 0.0,
        total_requests: int = 0,
        throughput_rps: float = 0.0,
        recorded_at: Optional[datetime] = None,
    ):
        self.id = id
        self.run_id = run_id
        self.p50_ms = p50_ms
        self.p95_ms = p95_ms
        self.p99_ms = p99_ms
        self.error_rate = error_rate
        self.total_requests = total_requests
        self.throughput_rps = throughput_rps
        self.recorded_at = recorded_at or datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "p50_ms": self.p50_ms,
            "p95_ms": self.p95_ms,
            "p99_ms": self.p99_ms,
            "error_rate": self.error_rate,
            "total_requests": self.total_requests,
            "throughput_rps": self.throughput_rps,
            "recorded_at": self.recorded_at.isoformat(),
        }


class TestRun:
    """A load test run instance."""

    def __init__(
        self,
        id: str,
        scenario_id: str,
        status: str = "pending",
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        results: Optional[list[dict]] = None,
    ):
        self.id = id
        self.scenario_id = scenario_id
        self.status = status
        self.started_at = started_at or datetime.utcnow()
        self.completed_at = completed_at
        self.results = results or []

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "scenario_id": self.scenario_id,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "results": self.results,
        }
