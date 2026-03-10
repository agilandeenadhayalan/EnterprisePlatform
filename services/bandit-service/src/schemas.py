"""
Pydantic response schemas for the Bandit service.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel


class BanditExperimentResponse(BaseModel):
    id: str
    name: str
    algorithm: str
    arms: List[Dict]
    epsilon: float
    created_at: str


class BanditListResponse(BaseModel):
    bandits: List[BanditExperimentResponse]
    total: int


class BanditCreateRequest(BaseModel):
    name: str
    algorithm: str
    arms: List[Dict] = []
    epsilon: float = 0.1


class PullResponse(BaseModel):
    arm_selected: str
    experiment_id: str


class RewardRequest(BaseModel):
    arm_name: str
    reward: float
    success: bool


class RewardResponse(BaseModel):
    experiment_id: str
    arm_name: str
    reward: float
    success: bool
    updated_arm: Dict


class BanditDecisionResponse(BaseModel):
    id: str
    experiment_id: str
    arm_selected: str
    reward: Optional[float] = None
    created_at: str


class DecisionListResponse(BaseModel):
    decisions: List[BanditDecisionResponse]
    total: int


class ArmStatsResponse(BaseModel):
    name: str
    successes: int
    failures: int
    total_reward: float
    pulls: int
    success_rate: float
    avg_reward: float


class BanditStatsResponse(BaseModel):
    experiment_id: str
    arms: List[ArmStatsResponse]
