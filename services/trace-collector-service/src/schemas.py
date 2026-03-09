"""
Pydantic response schemas for the Trace Collector service.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class SpanResponse(BaseModel):
    id: str
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    operation_name: str
    service_name: str
    start_time: str
    end_time: str
    duration_ms: float
    tags: Dict[str, Any]
    status: str


class SpanSubmitRequest(BaseModel):
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    operation_name: str
    service_name: str
    start_time: str
    end_time: str
    tags: Dict[str, Any] = {}
    status: str = "ok"


class TraceResponse(BaseModel):
    trace_id: str
    spans: List[SpanResponse]
    service_count: int
    total_duration_ms: float
    root_span: str


class TraceSummary(BaseModel):
    trace_id: str
    root_operation: str
    service_count: int
    duration_ms: float
    start_time: str


class TraceListResponse(BaseModel):
    traces: List[TraceSummary]
    total: int


class SpanListResponse(BaseModel):
    spans: List[SpanResponse]
    total: int


class ServiceDependencyResponse(BaseModel):
    source_service: str
    target_service: str
    call_count: int
    avg_duration_ms: float


class DependencyListResponse(BaseModel):
    dependencies: List[ServiceDependencyResponse]
    total: int


class AnalyzeRequest(BaseModel):
    service_name: str


class AnalyzeResponse(BaseModel):
    service_name: str
    span_count: int
    avg_duration_ms: float
    p50_ms: float
    p99_ms: float
    error_rate: float


class TraceStatsResponse(BaseModel):
    total_traces: int
    total_spans: int
    unique_services: int
    avg_spans_per_trace: float
    error_span_count: int
