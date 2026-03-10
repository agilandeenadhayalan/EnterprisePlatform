"""
Pydantic response schemas for the Fraud Detection service.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel


class FraudAlertResponse(BaseModel):
    id: str
    transaction_id: str
    user_id: str
    risk_score: float
    alert_type: str
    status: str
    details: Dict
    created_at: str


class FraudAlertListResponse(BaseModel):
    alerts: List[FraudAlertResponse]
    total: int


class FraudRuleResponse(BaseModel):
    id: str
    name: str
    rule_type: str
    threshold: float
    is_active: bool
    config: Dict
    created_at: str


class FraudRuleListResponse(BaseModel):
    rules: List[FraudRuleResponse]
    total: int


class FraudRuleCreateRequest(BaseModel):
    name: str
    rule_type: str
    threshold: float
    is_active: bool = True
    config: Dict = {}


class ScoreTransactionRequest(BaseModel):
    transaction_id: str
    user_id: str
    amount: float
    features: Dict = {}


class TransactionScoreResponse(BaseModel):
    transaction_id: str
    scores: Dict
    ensemble_score: float
    flagged: bool


class GraphAnalysisRequest(BaseModel):
    user_ids: List[str]


class GraphAnalysisResponse(BaseModel):
    user_ids: List[str]
    suspicious_patterns: List[Dict]
    risk_level: str


class FraudStatsResponse(BaseModel):
    total_alerts: int
    by_status: Dict[str, int]
    by_type: Dict[str, int]
    avg_risk_score: float
