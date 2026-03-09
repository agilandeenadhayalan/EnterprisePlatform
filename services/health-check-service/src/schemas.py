"""
Pydantic response schemas for the Health Check service.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel


class ServiceProbeResponse(BaseModel):
    id: str
    service_name: str
    probe_type: str
    endpoint: str
    timeout_seconds: int
    interval_seconds: int
    is_active: bool


class ServiceProbeListResponse(BaseModel):
    probes: List[ServiceProbeResponse]
    total: int


class ServiceProbeCreateRequest(BaseModel):
    service_name: str
    probe_type: str
    endpoint: str
    timeout_seconds: int = 5
    interval_seconds: int = 30
    is_active: bool = True


class HealthCheckResultResponse(BaseModel):
    id: str
    probe_id: str
    service_name: str
    status: str
    response_time_ms: float
    message: str
    checked_at: str


class HealthCheckResultListResponse(BaseModel):
    results: List[HealthCheckResultResponse]
    total: int


class ServiceStatusSummary(BaseModel):
    name: str
    status: str
    last_check: str
    response_time_ms: float


class DashboardResponse(BaseModel):
    services: List[ServiceStatusSummary]
    overall_status: str


class DependencyNodeResponse(BaseModel):
    service_name: str
    dependencies: List[str]
    status: str


class DependencyGraphResponse(BaseModel):
    nodes: List[DependencyNodeResponse]
    total: int


class HealthCheckStatsResponse(BaseModel):
    total_probes: int
    healthy_count: int
    unhealthy_count: int
    degraded_count: int
    avg_response_time_ms: float
