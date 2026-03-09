"""
Pydantic response schemas for the Feature Freshness Monitor service.
"""

from typing import List, Optional
from pydantic import BaseModel


class FreshnessStatusResponse(BaseModel):
    feature_name: str
    last_updated: str
    sla_seconds: int
    is_fresh: bool
    staleness_seconds: float


class FreshnessStatusListResponse(BaseModel):
    features: List[FreshnessStatusResponse]
    total: int
    fresh_count: int
    stale_count: int


class FreshnessViolationResponse(BaseModel):
    feature_name: str
    sla_seconds: int
    actual_staleness: float
    severity: str


class ViolationListResponse(BaseModel):
    violations: List[FreshnessViolationResponse]
    total: int


class DashboardResponse(BaseModel):
    total_features: int
    fresh_count: int
    stale_count: int
    freshness_percentage: float
    critical_violations: int
    warning_violations: int


class CheckRunResponse(BaseModel):
    checked: int
    fresh: int
    stale: int
    violations: int
    message: str


class SlaUpdateRequest(BaseModel):
    feature_name: str
    sla_seconds: int


class SlaUpdateResponse(BaseModel):
    feature_name: str
    sla_seconds: int
    message: str
