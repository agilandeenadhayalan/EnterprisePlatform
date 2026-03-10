"""
Pydantic response schemas for the RL Dispatch service.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel


class DispatchActionResponse(BaseModel):
    id: str
    state_id: str
    driver_id: str
    request_id: str
    action_type: str
    reward: Optional[float] = None
    policy_id: str
    created_at: str


class DispatchActionListResponse(BaseModel):
    actions: List[DispatchActionResponse]
    total: int


class DecideRequest(BaseModel):
    state: Dict = {}
    available_drivers: List[str] = []
    pending_requests: List[str] = []


class DecideResponse(BaseModel):
    action: DispatchActionResponse
    policy_used: str


class RewardRequest(BaseModel):
    action_id: str
    reward: float


class RewardResponse(BaseModel):
    action_id: str
    reward: float
    updated: bool


class DispatchPolicyResponse(BaseModel):
    id: str
    name: str
    algorithm: str
    parameters: Dict
    is_active: bool
    created_at: str


class PolicyListResponse(BaseModel):
    policies: List[DispatchPolicyResponse]
    total: int


class PolicyCreateRequest(BaseModel):
    name: str
    algorithm: str
    parameters: Dict = {}


class DispatchStatsResponse(BaseModel):
    total_actions: int
    by_policy: Dict[str, int]
    avg_reward: float
    active_policy: Optional[str] = None
