"""
Pydantic response schemas for the Metrics Aggregation service.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class MetricDefinitionResponse(BaseModel):
    id: str
    name: str
    metric_type: str
    description: str
    labels: List[str]
    unit: str


class MetricDefinitionListResponse(BaseModel):
    definitions: List[MetricDefinitionResponse]
    total: int


class MetricDefinitionCreateRequest(BaseModel):
    name: str
    metric_type: str
    description: str
    labels: List[str] = []
    unit: str = ""


class MetricDataPointResponse(BaseModel):
    id: str
    metric_name: str
    labels: Dict[str, Any]
    value: float
    timestamp: str


class MetricDataPointListResponse(BaseModel):
    data_points: List[MetricDataPointResponse]
    total: int


class MetricIngestRequest(BaseModel):
    metric_name: str
    labels: Dict[str, Any] = {}
    value: float
    timestamp: Optional[str] = None


class MetricQueryRequest(BaseModel):
    metric_name: str
    labels: Optional[Dict[str, Any]] = None
    time_start: Optional[str] = None
    time_end: Optional[str] = None


class MetricAggregateRequest(BaseModel):
    metric_name: str
    function: str
    labels: Optional[Dict[str, Any]] = None
    percentile: Optional[float] = None


class MetricAggregateResponse(BaseModel):
    result: float
    function: str
    metric_name: str


class RecordingRuleResponse(BaseModel):
    id: str
    name: str
    expression: str
    interval_seconds: int
    destination_metric: str


class RecordingRuleListResponse(BaseModel):
    rules: List[RecordingRuleResponse]
    total: int


class RecordingRuleCreateRequest(BaseModel):
    name: str
    expression: str
    interval_seconds: int = 300
    destination_metric: str


class MetricsStatsResponse(BaseModel):
    total_definitions: int
    total_data_points: int
    by_type: Dict[str, int]
