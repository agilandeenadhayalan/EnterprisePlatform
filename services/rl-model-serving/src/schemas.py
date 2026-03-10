"""
Pydantic response schemas for the RL Model Serving service.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel


class RLModelResponse(BaseModel):
    id: str
    name: str
    version: str
    algorithm: str
    status: str
    metrics: Dict
    created_at: str
    updated_at: str


class RLModelListResponse(BaseModel):
    models: List[RLModelResponse]
    total: int


class RegisterModelRequest(BaseModel):
    name: str
    version: str
    algorithm: str
    metrics: Dict = {}


class PredictRequest(BaseModel):
    model_id: str
    state_input: Dict


class PredictionResponse(BaseModel):
    id: str
    model_id: str
    state_input: Dict
    action_output: str
    confidence: float
    latency_ms: float
    created_at: str


class CompareRequest(BaseModel):
    model_a_id: str
    model_b_id: str
    metric: str


class ComparisonResponse(BaseModel):
    model_a_id: str
    model_b_id: str
    metric: str
    model_a_value: float
    model_b_value: float
    winner: str


class ModelStatsResponse(BaseModel):
    total_models: int
    by_status: Dict[str, int]
    by_algorithm: Dict[str, int]
    total_predictions: int
