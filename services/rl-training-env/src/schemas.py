"""
Pydantic response schemas for the RL Training Environment service.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel


class TrainingEpisodeResponse(BaseModel):
    id: str
    env_name: str
    policy_id: str
    steps: int
    total_reward: float
    epsilon: float
    status: str
    started_at: str
    completed_at: Optional[str] = None


class EpisodeListResponse(BaseModel):
    episodes: List[TrainingEpisodeResponse]
    total: int


class StartEpisodeRequest(BaseModel):
    env_name: str
    policy_id: str
    epsilon: float = 1.0


class StepRequest(BaseModel):
    state: Dict
    action: str
    reward: float
    next_state: Dict
    done: bool


class StepResponse(BaseModel):
    episode_id: str
    steps: int
    total_reward: float
    done: bool
    status: str


class TrainingConfigResponse(BaseModel):
    id: str
    env_name: str
    max_episodes: int
    max_steps: int
    learning_rate: float
    discount_factor: float
    epsilon_start: float
    epsilon_end: float
    buffer_size: int


class ConfigListResponse(BaseModel):
    configs: List[TrainingConfigResponse]
    total: int


class CreateConfigRequest(BaseModel):
    env_name: str
    max_episodes: int = 1000
    max_steps: int = 200
    learning_rate: float = 0.001
    discount_factor: float = 0.99
    epsilon_start: float = 1.0
    epsilon_end: float = 0.01
    buffer_size: int = 10000


class TrainingStatsResponse(BaseModel):
    total_episodes: int
    by_status: Dict[str, int]
    by_env: Dict[str, int]
    avg_reward: float
    avg_steps: float
