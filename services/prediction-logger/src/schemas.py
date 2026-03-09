"""
Pydantic response schemas for the Prediction Logger service.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


# ── Request schemas ──

class PredictionLogRequest(BaseModel):
    model_name: str
    model_version: str
    features: Dict[str, Any]
    prediction: float
    confidence: float
    latency_ms: float
    request_source: str = "api"


class PredictionLogBatchRequest(BaseModel):
    predictions: List[PredictionLogRequest]


# ── Response schemas ──

class PredictionLogResponse(BaseModel):
    id: str
    model_name: str
    model_version: str
    features: Dict[str, Any]
    prediction: float
    confidence: float
    latency_ms: float
    request_source: str
    timestamp: str


class PredictionLogListResponse(BaseModel):
    predictions: List[PredictionLogResponse]
    total: int


class PredictionLogCreateResponse(BaseModel):
    id: str
    message: str


class PredictionLogBatchResponse(BaseModel):
    logged: int
    message: str


class PredictionStatsResponse(BaseModel):
    model_name: str
    total_predictions: int
    avg_confidence: float
    avg_latency_ms: float
    predictions_today: int
    predictions_this_hour: int


class PredictionStatsListResponse(BaseModel):
    stats: List[PredictionStatsResponse]
    total_models: int
