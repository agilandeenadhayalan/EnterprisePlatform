"""
Pydantic response schemas for the Feature Pipeline Zone service.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ZoneFeatureSetResponse(BaseModel):
    zone_id: str
    hour: str
    features: Dict[str, Any]
    computed_at: str


class ZoneFeatureSetListResponse(BaseModel):
    feature_sets: List[ZoneFeatureSetResponse]
    total: int


class PipelineRunResponse(BaseModel):
    id: str
    status: str
    start_time: str
    end_time: Optional[str]
    features_computed: int


class PipelineRunRequest(BaseModel):
    zone_ids: Optional[List[str]] = None


class CatalogEntry(BaseModel):
    name: str
    description: str
    value_type: str
    source: str


class CatalogResponse(BaseModel):
    features: List[CatalogEntry]
    total: int


class TimeseriesResponse(BaseModel):
    zone_id: str
    timeseries: List[ZoneFeatureSetResponse]
    total: int
