"""
Pydantic response schemas for the Log Aggregation service.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class LogEntryResponse(BaseModel):
    id: str
    timestamp: str
    service_name: str
    level: str
    message: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    fields: Dict[str, Any]


class LogEntryListResponse(BaseModel):
    entries: List[LogEntryResponse]
    total: int


class LogIngestRequest(BaseModel):
    service_name: str
    level: str
    message: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    fields: Dict[str, Any] = {}


class LogQueryRequest(BaseModel):
    service_name: Optional[str] = None
    level: Optional[str] = None
    time_start: Optional[str] = None
    time_end: Optional[str] = None
    search: Optional[str] = None
    limit: int = 100


class LogPatternResponse(BaseModel):
    id: str
    pattern: str
    count: int
    first_seen: str
    last_seen: str
    sample_message: str


class LogPatternListResponse(BaseModel):
    patterns: List[LogPatternResponse]
    total: int


class RetentionPolicyResponse(BaseModel):
    id: str
    name: str
    service_filter: str
    level_filter: str
    retention_days: int
    is_active: bool


class RetentionPolicyListResponse(BaseModel):
    policies: List[RetentionPolicyResponse]
    total: int


class RetentionPolicyCreateRequest(BaseModel):
    name: str
    service_filter: str = "*"
    level_filter: str = "*"
    retention_days: int = 30
    is_active: bool = True


class LogStatsResponse(BaseModel):
    total_entries: int
    by_level: Dict[str, int]
    by_service: Dict[str, int]
    entries_with_traces: int
