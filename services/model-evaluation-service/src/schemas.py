"""
Pydantic request/response schemas for the model evaluation API.
"""

from typing import Optional

from pydantic import BaseModel, Field


# ── Request schemas ──


class EvaluationRunRequest(BaseModel):
    """Request to run an evaluation."""
    model_name: str = Field(..., description="Name of the model to evaluate")
    model_version: str = Field(..., description="Version of the model")
    dataset_id: str = Field(..., description="ID of the evaluation dataset")


class CompareRequest(BaseModel):
    """Request to compare two models."""
    model_a: str = Field(..., description="First model name")
    model_b: str = Field(..., description="Second model name")
    dataset_id: str = Field(..., description="Dataset to compare on")


# ── Response schemas ──


class EvaluationResultResponse(BaseModel):
    """Evaluation result details."""
    id: str
    model_name: str
    model_version: str
    dataset_id: str
    task_type: str
    metrics: dict
    evaluated_at: str


class EvaluationResultListResponse(BaseModel):
    """List of evaluation results."""
    results: list[EvaluationResultResponse]
    total: int


class ModelComparisonResponse(BaseModel):
    """Model comparison result."""
    model_a: str
    model_b: str
    dataset_id: str
    metrics_a: dict
    metrics_b: dict
    winner: str
    improvement_pct: float


class LeaderboardEntry(BaseModel):
    """A single leaderboard entry."""
    rank: int
    model_name: str
    model_version: str
    metric_value: float
    dataset_id: str
    evaluated_at: str


class LeaderboardResponse(BaseModel):
    """Model leaderboard."""
    entries: list[LeaderboardEntry]
    metric: str
    task: str
    total: int
