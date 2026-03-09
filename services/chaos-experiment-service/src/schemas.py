"""
Pydantic response schemas for the Chaos Experiment service.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ChaosExperimentResponse(BaseModel):
    id: str
    name: str
    experiment_type: str
    target_service: str
    blast_radius: str
    duration_seconds: int
    status: str
    created_at: str
    parameters: Dict[str, Any]


class ChaosExperimentListResponse(BaseModel):
    experiments: List[ChaosExperimentResponse]
    total: int


class ChaosExperimentCreateRequest(BaseModel):
    name: str
    experiment_type: str
    target_service: str
    blast_radius: str = "single-service"
    duration_seconds: int = 60
    status: str = "draft"
    parameters: Dict[str, Any] = {}


class ChaosRunResponse(BaseModel):
    id: str
    experiment_id: str
    started_at: str
    ended_at: Optional[str] = None
    steady_state_before: Dict[str, Any]
    steady_state_after: Dict[str, Any]
    result: str
    impact_summary: Dict[str, Any]


class ChaosRunListResponse(BaseModel):
    runs: List[ChaosRunResponse]
    total: int


class SteadyStateHypothesisResponse(BaseModel):
    id: str
    experiment_id: str
    metric_name: str
    operator: str
    threshold: float
    description: str


class BlastRadiusResponse(BaseModel):
    experiment_id: str
    blast_radius: str
    target_service: str
    affected_services: List[str]
    estimated_impact: str


class VerificationResultItem(BaseModel):
    metric: str
    expected: str
    actual: float
    passed: bool


class VerificationResponse(BaseModel):
    passed: bool
    results: List[VerificationResultItem]


class ChaosStatsResponse(BaseModel):
    total_experiments: int
    total_runs: int
    pass_rate: float
    by_type: Dict[str, int]
    by_result: Dict[str, int]
