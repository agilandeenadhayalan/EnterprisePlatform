"""
Pydantic request/response schemas for the Hyperparameter Tuner API.
"""

from typing import Optional

from pydantic import BaseModel, Field


# ── Request schemas ──


class ParamSpaceRequest(BaseModel):
    """Definition of a parameter search space."""
    param_name: str
    type: str = Field(..., description="Parameter type: int, float, categorical")
    min: Optional[float] = None
    max: Optional[float] = None
    choices: Optional[list] = None


class SearchCreateRequest(BaseModel):
    """Request to create a hyperparameter search."""
    model_type: str = Field(..., description="Model architecture name")
    search_strategy: str = Field(default="grid", description="Search strategy: grid, random, bayesian")
    param_space: list[ParamSpaceRequest] = Field(..., description="Parameter search spaces")
    objective_metric: str = Field(default="val_loss", description="Metric to optimize")


# ── Response schemas ──


class ParamSpaceResponse(BaseModel):
    """A parameter space definition."""
    param_name: str
    type: str
    min: Optional[float] = None
    max: Optional[float] = None
    choices: Optional[list] = None


class SearchTrialResponse(BaseModel):
    """A single search trial with params and metrics."""
    id: str
    search_id: str
    params: dict
    metrics: dict
    status: str
    duration_seconds: float


class HyperparameterSearchResponse(BaseModel):
    """A hyperparameter search session."""
    id: str
    model_type: str
    search_strategy: str
    param_space: list[ParamSpaceResponse]
    objective_metric: str
    status: str
    best_trial_id: Optional[str] = None
    created_at: str


class SearchListResponse(BaseModel):
    """List of hyperparameter searches."""
    searches: list[HyperparameterSearchResponse]
    total: int


class TrialListResponse(BaseModel):
    """List of search trials."""
    trials: list[SearchTrialResponse]
    total: int
