"""
Pydantic response schemas for the Demand Simulator service.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel


class DemandScenarioResponse(BaseModel):
    id: str
    name: str
    pattern_type: str
    parameters: Dict
    duration_hours: int
    created_at: str


class DemandScenarioListResponse(BaseModel):
    scenarios: List[DemandScenarioResponse]
    total: int


class DemandScenarioCreateRequest(BaseModel):
    name: str
    pattern_type: str
    parameters: Dict = {}
    duration_hours: int = 1


class SimulationRunResponse(BaseModel):
    id: str
    scenario_id: str
    status: str
    generated_events: int
    results: Dict
    started_at: str
    completed_at: Optional[str] = None


class SimulationRunListResponse(BaseModel):
    runs: List[SimulationRunResponse]
    total: int


class SimulatorStatsResponse(BaseModel):
    total_scenarios: int
    total_runs: int
    by_status: Dict[str, int]
    avg_events: float
