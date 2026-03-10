"""
Pydantic response schemas for the Experiment service.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel


class ExperimentResponse(BaseModel):
    id: str
    name: str
    description: str
    experiment_type: str
    status: str
    variants: List[Dict]
    targeting_rules: List[Dict]
    traffic_percentage: float
    created_at: str
    updated_at: str


class ExperimentListResponse(BaseModel):
    experiments: List[ExperimentResponse]
    total: int


class ExperimentCreateRequest(BaseModel):
    name: str
    description: str = ""
    experiment_type: str
    variants: List[Dict] = []
    targeting_rules: List[Dict] = []
    traffic_percentage: float = 100.0


class ExperimentUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    variants: Optional[List[Dict]] = None
    targeting_rules: Optional[List[Dict]] = None
    traffic_percentage: Optional[float] = None


class ExperimentStatsResponse(BaseModel):
    total: int
    by_status: Dict[str, int]
    by_type: Dict[str, int]
