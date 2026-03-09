"""
Pydantic request/response schemas for the Experiment Tracker API.
"""

from typing import Optional

from pydantic import BaseModel, Field


# ── Request schemas ──


class ExperimentCreateRequest(BaseModel):
    """Request to create a new experiment."""
    name: str = Field(..., description="Experiment name")
    description: str = Field(default="", description="Experiment description")


class RunCreateRequest(BaseModel):
    """Request to log a new run."""
    run_name: str = Field(..., description="Run name")
    params: dict = Field(default_factory=dict, description="Run parameters")
    metrics: dict = Field(default_factory=dict, description="Run metrics")
    artifacts: list[str] = Field(default_factory=list, description="Artifact paths")
    status: str = Field(default="completed", description="Run status")


# ── Response schemas ──


class ExperimentResponse(BaseModel):
    """An experiment."""
    id: str
    name: str
    description: str
    created_at: str


class ExperimentListResponse(BaseModel):
    """List of experiments."""
    experiments: list[ExperimentResponse]
    total: int


class RunResponse(BaseModel):
    """An experiment run."""
    id: str
    experiment_id: str
    run_name: str
    params: dict
    metrics: dict
    artifacts: list[str]
    status: str
    start_time: str
    end_time: Optional[str] = None


class RunListResponse(BaseModel):
    """List of runs."""
    runs: list[RunResponse]
    total: int


class MetricRunEntry(BaseModel):
    """A single run's value for a metric."""
    run_id: str
    run_name: str
    value: float


class MetricComparisonResponse(BaseModel):
    """Comparison of a metric across runs."""
    metric_name: str
    runs: list[MetricRunEntry]


class CompareResponse(BaseModel):
    """Metric comparisons across runs."""
    experiment_id: str
    comparisons: list[MetricComparisonResponse]
