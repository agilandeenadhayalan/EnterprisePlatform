"""
Pydantic request/response schemas for the ML Training Service API.
"""

from typing import Optional

from pydantic import BaseModel, Field


# ── Request schemas ──


class TrainingJobCreateRequest(BaseModel):
    """Request to submit a new training job."""
    model_type: str = Field(..., description="Model architecture name")
    hyperparameters: dict = Field(default_factory=dict, description="Training hyperparameters")
    dataset_id: str = Field(..., description="Dataset ID to train on")


# ── Response schemas ──


class TrainingMetricsResponse(BaseModel):
    """Metrics for a single training epoch."""
    epoch: int
    train_loss: float
    val_loss: float
    train_metric: float
    val_metric: float


class TrainingJobResponse(BaseModel):
    """A training job with full details."""
    id: str
    model_type: str
    hyperparameters: dict
    dataset_id: str
    status: str
    metrics: list[TrainingMetricsResponse]
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    logs: list[str]


class TrainingJobListResponse(BaseModel):
    """List of training jobs."""
    jobs: list[TrainingJobResponse]
    total: int


class ModelArchitectureResponse(BaseModel):
    """A model architecture definition."""
    name: str
    type: str
    description: str
    default_hyperparameters: dict


class ModelArchitectureListResponse(BaseModel):
    """List of model architectures."""
    architectures: list[ModelArchitectureResponse]
    total: int


class TrainingLogResponse(BaseModel):
    """Training logs for a job."""
    job_id: str
    logs: list[str]
    total: int
