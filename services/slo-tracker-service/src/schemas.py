"""
Pydantic response schemas for the SLO Tracker service.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel


class SloDefinitionResponse(BaseModel):
    id: str
    service_name: str
    slo_type: str
    target_percentage: float
    window_days: int
    description: str
    created_at: str


class SloDefinitionListResponse(BaseModel):
    slos: List[SloDefinitionResponse]
    total: int


class SloCreateRequest(BaseModel):
    service_name: str
    slo_type: str
    target_percentage: float
    window_days: int = 30
    description: str = ""


class SloRecordResponse(BaseModel):
    id: str
    slo_id: str
    period_start: str
    period_end: str
    good_events: int
    total_events: int
    actual_percentage: float
    error_budget_remaining: float


class SloRecordListResponse(BaseModel):
    records: List[SloRecordResponse]
    total: int


class SloRecordCreateRequest(BaseModel):
    good_events: int
    total_events: int


class ErrorBudgetResponse(BaseModel):
    slo_id: str
    target: float
    current_percentage: float
    error_budget_total: float
    error_budget_remaining: float
    error_budget_consumed_percent: float
    burn_rate: float
    is_budget_exhausted: bool


class BurnRateAlertResponse(BaseModel):
    id: str
    slo_id: str
    burn_rate: float
    threshold: float
    is_critical: bool
    created_at: str
    message: str


class BurnRateAlertListResponse(BaseModel):
    alerts: List[BurnRateAlertResponse]
    total: int


class SloStatsResponse(BaseModel):
    total_slos: int
    slos_meeting_target: int
    slos_at_risk: int
    avg_error_budget_remaining: float
    by_type: Dict[str, int]
