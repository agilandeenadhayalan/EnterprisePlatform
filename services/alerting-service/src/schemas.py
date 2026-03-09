"""
Pydantic response schemas for the Alerting service.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel


class AlertRuleResponse(BaseModel):
    id: str
    name: str
    severity: str
    condition_type: str
    condition_config: Dict
    channel: str
    is_active: bool
    created_at: str
    updated_at: str


class AlertRuleListResponse(BaseModel):
    rules: List[AlertRuleResponse]
    total: int


class AlertRuleCreateRequest(BaseModel):
    name: str
    severity: str
    condition_type: str
    condition_config: Dict = {}
    channel: str
    is_active: bool = True


class AlertEventResponse(BaseModel):
    id: str
    rule_id: str
    rule_name: str
    severity: str
    status: str
    fired_at: str
    resolved_at: Optional[str] = None
    acknowledged_by: Optional[str] = None
    message: str


class AlertEventListResponse(BaseModel):
    events: List[AlertEventResponse]
    total: int


class AlertFireRequest(BaseModel):
    rule_id: str
    message: str


class AlertAcknowledgeRequest(BaseModel):
    acknowledged_by: str


class AlertRoutingResponse(BaseModel):
    id: str
    channel: str
    severity_filter: List[str]
    endpoint: str
    is_active: bool


class AlertRoutingListResponse(BaseModel):
    routing_rules: List[AlertRoutingResponse]
    total: int


class AlertStatsResponse(BaseModel):
    total_rules: int
    active_rules: int
    firing_alerts: int
    resolved_alerts: int
    by_severity: Dict[str, int]
