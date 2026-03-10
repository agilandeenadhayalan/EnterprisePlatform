"""
Pydantic request/response schemas for the load test service API.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Request schemas ──

class ScenarioCreate(BaseModel):
    """POST /load-tests/scenarios — create a test scenario."""
    name: str = Field(..., description="Scenario name")
    pattern: str = Field(default="ramp", description="Load pattern: ramp, spike, soak, stress")
    target_rps: int = Field(default=100, description="Target requests per second")
    duration_seconds: int = Field(default=60, description="Test duration in seconds")
    config: Optional[dict[str, Any]] = Field(default=None, description="Additional config")


class RunCreate(BaseModel):
    """POST /load-tests/runs — start a load test run."""
    scenario_id: str = Field(..., description="Scenario ID to run")


class RunUpdate(BaseModel):
    """PATCH /load-tests/runs/{id} — update run status/results."""
    status: Optional[str] = None
    completed_at: Optional[datetime] = None


class ResultCreate(BaseModel):
    """POST /load-tests/runs/{id}/results — record results."""
    p50_ms: float = Field(default=0.0, description="50th percentile latency")
    p95_ms: float = Field(default=0.0, description="95th percentile latency")
    p99_ms: float = Field(default=0.0, description="99th percentile latency")
    error_rate: float = Field(default=0.0, description="Error rate (0.0-1.0)")
    total_requests: int = Field(default=0, description="Total requests made")
    throughput_rps: float = Field(default=0.0, description="Actual throughput RPS")


# ── Response schemas ──

class ScenarioResponse(BaseModel):
    """A test scenario."""
    id: str
    name: str
    pattern: str
    target_rps: int
    duration_seconds: int
    config: dict[str, Any] = {}
    created_at: datetime


class RunResponse(BaseModel):
    """A test run."""
    id: str
    scenario_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    results: list[dict[str, Any]] = []


class ResultResponse(BaseModel):
    """A test result."""
    id: str
    run_id: str
    p50_ms: float
    p95_ms: float
    p99_ms: float
    error_rate: float
    total_requests: int
    throughput_rps: float
    recorded_at: datetime


class AnalysisResponse(BaseModel):
    """Latency analysis for a run."""
    run_id: str
    num_results: int
    avg_p50_ms: float
    avg_p95_ms: float
    avg_p99_ms: float
    avg_error_rate: float
    total_requests: int
    avg_throughput_rps: float
