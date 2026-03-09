"""
Pydantic response schemas for the ML Monitoring service.
"""

from typing import List, Optional
from pydantic import BaseModel


# ── Request schemas ──

class DriftDetectRequest(BaseModel):
    feature_name: str
    reference_data: List[float]
    current_data: List[float]
    method: str = "psi"


class ReferenceSetRequest(BaseModel):
    feature_name: str
    values: List[float]


class ConceptDriftRequest(BaseModel):
    model_name: str
    predictions: List[float]
    actuals: List[float]


# ── Response schemas ──

class DriftResultResponse(BaseModel):
    id: str
    feature_name: str
    drift_type: str
    metric_name: str
    metric_value: float
    threshold: float
    is_drifted: bool
    detected_at: str


class DriftResultListResponse(BaseModel):
    results: List[DriftResultResponse]
    total: int


class ReferenceDistributionResponse(BaseModel):
    feature_name: str
    values: List[float]
    mean: float
    std: float
    num_bins: int
    set_at: str


class DriftAlertResponse(BaseModel):
    id: str
    feature_name: str
    drift_type: str
    severity: str
    message: str
    created_at: str


class DriftAlertListResponse(BaseModel):
    alerts: List[DriftAlertResponse]
    total: int


class ConceptDriftResultResponse(BaseModel):
    model_name: str
    error_mean: float
    error_trend: float
    is_drifted: bool


class DashboardFeature(BaseModel):
    feature_name: str
    latest_result: Optional[DriftResultResponse] = None
    has_reference: bool
    alert_count: int


class DriftDashboardResponse(BaseModel):
    features: List[DashboardFeature]
    total_features: int
    drifted_count: int
