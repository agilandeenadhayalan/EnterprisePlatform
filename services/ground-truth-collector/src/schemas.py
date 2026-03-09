"""
Pydantic response schemas for the Ground Truth Collector service.
"""

from typing import List, Optional
from pydantic import BaseModel


# ── Request schemas ──

class LabelItem(BaseModel):
    prediction_id: str
    model_name: str
    actual_value: float


class LabelsSubmitRequest(BaseModel):
    labels: List[LabelItem]


class JoinRequest(BaseModel):
    model_name: str


# ── Response schemas ──

class GroundTruthLabelResponse(BaseModel):
    id: str
    prediction_id: str
    model_name: str
    actual_value: float
    label_timestamp: str
    delay_seconds: float


class LabelListResponse(BaseModel):
    labels: List[GroundTruthLabelResponse]
    total: int


class LabelsSubmitResponse(BaseModel):
    ingested: int
    message: str


class PredictionGroundTruthPairResponse(BaseModel):
    prediction_id: str
    predicted_value: float
    actual_value: float
    error: float
    model_name: str


class JoinResponse(BaseModel):
    model_name: str
    pairs: List[PredictionGroundTruthPairResponse]
    total: int


class LabelCoverageResponse(BaseModel):
    model_name: str
    total_predictions: int
    labeled_predictions: int
    coverage_pct: float


class CoverageListResponse(BaseModel):
    coverage: List[LabelCoverageResponse]
    total_models: int


class PerformanceBucket(BaseModel):
    bucket: str
    mae: float
    count: int


class ModelPerformance(BaseModel):
    model_name: str
    overall_mae: float
    buckets: List[PerformanceBucket]


class PerformanceResponse(BaseModel):
    models: List[ModelPerformance]
    total_models: int
