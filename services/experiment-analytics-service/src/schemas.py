"""
Pydantic response schemas for the Experiment Analytics service.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel


class ExperimentAnalysisResponse(BaseModel):
    id: str
    experiment_id: str
    metric_name: str
    control_mean: float
    variant_mean: float
    p_value: float
    significant: bool
    effect_size: float
    sample_size: int
    created_at: str


class ExperimentAnalysisListResponse(BaseModel):
    analyses: List[ExperimentAnalysisResponse]
    total: int


class AnalyzeExperimentRequest(BaseModel):
    experiment_id: str
    metric_name: str
    control_data: List[float]
    variant_data: List[float]


class SegmentAnalysisRequest(BaseModel):
    experiment_id: str
    segments: Dict[str, Dict]


class SegmentAnalysisResponse(BaseModel):
    experiment_id: str
    segments: List[Dict]


class AnalysisReportResponse(BaseModel):
    id: str
    experiment_id: str
    analyses: List[Dict]
    segments: List[Dict]
    recommendation: str
    created_at: str


class AnalysisReportListResponse(BaseModel):
    reports: List[AnalysisReportResponse]
    total: int


class ExperimentStatsResponse(BaseModel):
    total_analyses: int
    significant_count: int
    avg_effect_size: float
