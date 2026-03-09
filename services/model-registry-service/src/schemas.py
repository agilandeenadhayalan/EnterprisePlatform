"""
Pydantic request/response schemas for the model registry API.
"""

from typing import Optional

from pydantic import BaseModel, Field


# ── Request schemas ──


class RegisterModelRequest(BaseModel):
    """Request to register a new model."""
    name: str = Field(..., description="Model name")
    description: str = Field(default="", description="Model description")
    model_type: str = Field(default="sklearn", description="Model framework (sklearn, xgboost, pytorch, etc.)")
    task_type: str = Field(default="regression", description="Task type (regression, classification, etc.)")


class CreateVersionRequest(BaseModel):
    """Request to create a new model version."""
    run_id: Optional[str] = Field(default=None, description="MLflow run ID")
    metrics: Optional[dict] = Field(default=None, description="Model metrics")
    hyperparameters: Optional[dict] = Field(default=None, description="Model hyperparameters")


class StageTransitionRequest(BaseModel):
    """Request to transition a model version's stage."""
    stage: str = Field(..., description="Target stage: none, staging, production, archived")
    reason: str = Field(default="", description="Reason for transition")


# ── Response schemas ──


class ModelVersionResponse(BaseModel):
    """Model version details."""
    version: int
    model_name: str
    stage: str
    run_id: Optional[str] = None
    metrics: dict
    hyperparameters: dict
    created_at: str
    transitioned_at: Optional[str] = None


class ModelVersionListResponse(BaseModel):
    """List of model versions."""
    versions: list[ModelVersionResponse]
    total: int


class RegisteredModelResponse(BaseModel):
    """Registered model details."""
    name: str
    description: str
    model_type: str
    task_type: str
    latest_version: Optional[int] = None
    production_version: Optional[int] = None
    created_at: str


class RegisteredModelDetailResponse(BaseModel):
    """Registered model with all versions."""
    name: str
    description: str
    model_type: str
    task_type: str
    latest_version: Optional[int] = None
    production_version: Optional[int] = None
    created_at: str
    versions: list[ModelVersionResponse]


class RegisteredModelListResponse(BaseModel):
    """List of registered models."""
    models: list[RegisteredModelResponse]
    total: int


class StageTransitionResponse(BaseModel):
    """Stage transition result."""
    from_stage: str
    to_stage: str
    reason: str
    version: ModelVersionResponse
