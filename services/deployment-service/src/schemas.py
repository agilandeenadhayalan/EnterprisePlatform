"""
Pydantic response schemas for the Deployment service.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel


class DeploymentResponse(BaseModel):
    id: str
    service_name: str
    version: str
    strategy: str
    environment: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    rolled_back: bool
    canary_percentage: Optional[int] = None
    previous_version: Optional[str] = None


class DeploymentListResponse(BaseModel):
    deployments: List[DeploymentResponse]
    total: int


class DeploymentCreateRequest(BaseModel):
    service_name: str
    version: str
    strategy: str
    environment: str


class DeploymentEventResponse(BaseModel):
    id: str
    deployment_id: str
    action: str
    details: Dict
    timestamp: str


class DeploymentEventListResponse(BaseModel):
    events: List[DeploymentEventResponse]
    total: int


class EnvironmentResponse(BaseModel):
    name: str
    current_version: str
    last_deployed_at: str
    is_locked: bool


class EnvironmentListResponse(BaseModel):
    environments: List[EnvironmentResponse]
    total: int


class DeploymentStatsResponse(BaseModel):
    total: int
    by_status: Dict[str, int]
    by_strategy: Dict[str, int]
    by_environment: Dict[str, int]
    rollback_rate: float
