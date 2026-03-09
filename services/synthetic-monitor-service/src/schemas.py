"""
Pydantic response schemas for the Synthetic Monitor service.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel


class SyntheticMonitorResponse(BaseModel):
    id: str
    name: str
    monitor_type: str
    target_url: str
    interval_seconds: int
    timeout_seconds: int
    expected_status_code: int
    is_active: bool
    created_at: str


class SyntheticMonitorListResponse(BaseModel):
    monitors: List[SyntheticMonitorResponse]
    total: int


class SyntheticMonitorCreateRequest(BaseModel):
    name: str
    monitor_type: str
    target_url: str
    interval_seconds: int = 60
    timeout_seconds: int = 30
    expected_status_code: int = 200
    is_active: bool = True


class SyntheticResultResponse(BaseModel):
    id: str
    monitor_id: str
    monitor_name: str
    status_code: int
    response_time_ms: float
    is_success: bool
    error_message: Optional[str] = None
    checked_at: str


class SyntheticResultListResponse(BaseModel):
    results: List[SyntheticResultResponse]
    total: int


class UptimeReportResponse(BaseModel):
    monitor_id: str
    monitor_name: str
    period_hours: int
    total_checks: int
    successful_checks: int
    uptime_percentage: float
    avg_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float


class SyntheticStatsResponse(BaseModel):
    total_monitors: int
    active_monitors: int
    total_checks: int
    overall_uptime_percentage: float
    avg_response_time_ms: float
