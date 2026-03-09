"""
Pydantic response schemas for the Feature Pipeline Driver service.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class DriverFeatureSetResponse(BaseModel):
    driver_id: str
    features: Dict[str, Any]
    computed_at: str


class DriverFeatureSetListResponse(BaseModel):
    feature_sets: List[DriverFeatureSetResponse]
    total: int


class PipelineRunResponse(BaseModel):
    id: str
    status: str
    start_time: str
    end_time: Optional[str]
    features_computed: int


class PipelineStatusResponse(BaseModel):
    runs: List[PipelineRunResponse]
    total_runs: int
    last_run_status: Optional[str]


class PipelineRunRequest(BaseModel):
    driver_ids: Optional[List[str]] = None


class CatalogEntry(BaseModel):
    name: str
    description: str
    value_type: str
    source: str


class CatalogResponse(BaseModel):
    features: List[CatalogEntry]
    total: int
