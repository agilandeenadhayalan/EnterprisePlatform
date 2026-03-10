"""
Pydantic response schemas for the AB Test Analytics service.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel


class ABTestResultResponse(BaseModel):
    id: str
    experiment_id: str
    metric: str
    control_count: int
    control_conversions: int
    variant_count: int
    variant_conversions: int
    z_score: float
    p_value: float
    significant: bool
    created_at: str


class ABTestResultListResponse(BaseModel):
    results: List[ABTestResultResponse]
    total: int


class RunTestRequest(BaseModel):
    experiment_id: str
    metric: str
    control_count: int
    control_conversions: int
    variant_count: int
    variant_conversions: int


class PowerCalcRequest(BaseModel):
    alpha: float = 0.05
    power: float = 0.8
    mde: float = 0.05


class PowerCalcResponse(BaseModel):
    sample_size_needed: int
    power: float
    alpha: float
    minimum_detectable_effect: float


class SequentialTestRequest(BaseModel):
    experiment_id: str
    observations: int
    successes: int
    alpha: float = 0.05


class SequentialTestResultResponse(BaseModel):
    id: str
    experiment_id: str
    observations: int
    current_z: float
    boundary: float
    stopped_early: bool
    created_at: str


class SequentialTestListResponse(BaseModel):
    results: List[SequentialTestResultResponse]
    total: int


class ABTestStatsResponse(BaseModel):
    total_tests: int
    significant_count: int
    avg_z_score: float
