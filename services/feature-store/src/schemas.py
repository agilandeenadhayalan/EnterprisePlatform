"""
Pydantic response schemas for the Feature Store service.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class FeatureDefinitionResponse(BaseModel):
    name: str
    entity_type: str
    value_type: str
    source: str
    description: str
    freshness_sla_seconds: int
    is_active: bool
    created_at: str


class FeatureDefinitionListResponse(BaseModel):
    definitions: List[FeatureDefinitionResponse]
    total: int


class FeatureDefinitionCreateRequest(BaseModel):
    name: str
    entity_type: str
    value_type: str
    source: str
    description: str
    freshness_sla_seconds: int = 3600
    is_active: bool = True


class FeatureValueResponse(BaseModel):
    entity_id: str
    feature_name: str
    value: float
    timestamp: str


class FeatureVectorResponse(BaseModel):
    entity_id: str
    features: Dict[str, Any]
    retrieved_at: str


class OnlineFeatureRequest(BaseModel):
    entity_id: str
    feature_names: List[str]


class OfflineFeatureRequest(BaseModel):
    entity_ids: List[str]
    feature_names: List[str]


class OfflineFeatureResponse(BaseModel):
    vectors: List[FeatureVectorResponse]
    total: int


class IngestRequest(BaseModel):
    entity_id: str
    feature_name: str
    value: float
    timestamp: Optional[str] = None


class IngestResponse(BaseModel):
    ingested: int
    message: str


class FeatureStatsResponse(BaseModel):
    total_definitions: int
    active_definitions: int
    total_values: int
    entity_types: List[str]
    sources: List[str]
