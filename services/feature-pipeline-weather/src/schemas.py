"""
Pydantic response schemas for the Feature Pipeline Weather service.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class WeatherFeatureSetResponse(BaseModel):
    station_id: str
    hour: str
    features: Dict[str, Any]
    computed_at: str


class WeatherFeatureSetListResponse(BaseModel):
    feature_sets: List[WeatherFeatureSetResponse]
    total: int


class PipelineRunResponse(BaseModel):
    id: str
    status: str
    start_time: str
    end_time: Optional[str]
    features_computed: int


class PipelineRunRequest(BaseModel):
    station_ids: Optional[List[str]] = None


class CatalogEntry(BaseModel):
    name: str
    description: str
    value_type: str
    source: str


class CatalogResponse(BaseModel):
    features: List[CatalogEntry]
    total: int


class WeatherFeaturesQuery(BaseModel):
    station_id: str
    hour: Optional[str] = None
