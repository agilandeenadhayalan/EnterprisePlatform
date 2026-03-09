"""
Pydantic request/response schemas for the prediction API.
"""

from typing import Optional

from pydantic import BaseModel, Field


# ── Request schemas ──


class PredictionRequest(BaseModel):
    """Single prediction request."""
    model_name: str = Field(..., description="Name of the model to use")
    features: dict = Field(..., description="Feature dict for prediction")


class BatchPredictionRequest(BaseModel):
    """Batch prediction request."""
    model_name: str = Field(..., description="Name of the model to use")
    instances: list[dict] = Field(..., description="List of feature dicts")


class ModelLoadRequest(BaseModel):
    """Request to load or reload a model."""
    version: Optional[str] = Field(default=None, description="Model version to load")


# ── Response schemas ──


class PredictionResponse(BaseModel):
    """Single prediction response."""
    prediction: float
    confidence: float
    model_name: str
    model_version: str
    latency_ms: float


class BatchPredictionResponse(BaseModel):
    """Batch prediction response."""
    predictions: list[PredictionResponse]
    total: int
    avg_latency_ms: float


class LoadedModelResponse(BaseModel):
    """Loaded model metadata."""
    name: str
    version: str
    loaded_at: str
    request_count: int
    avg_latency_ms: float
    total_predictions: int


class LoadedModelListResponse(BaseModel):
    """List of loaded models."""
    models: list[LoadedModelResponse]
    total: int


class LatencyStatsResponse(BaseModel):
    """Latency statistics across all models."""
    models: list[LoadedModelResponse]
    overall_avg_latency_ms: float
    total_requests: int
