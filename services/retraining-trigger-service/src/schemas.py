"""
Pydantic request/response schemas for the Retraining Trigger Service API.
"""

from typing import Optional

from pydantic import BaseModel, Field


# ── Request schemas ──


class TriggerCreateRequest(BaseModel):
    """Request to create a retraining trigger rule."""
    model_name: str = Field(..., description="Name of the model to monitor")
    trigger_type: str = Field(..., description="Trigger type: drift, performance, scheduled")
    condition: str = Field(..., description="Condition expression (e.g., 'psi > threshold')")
    threshold: float = Field(..., description="Threshold value for the condition")
    cooldown_hours: int = Field(default=24, description="Minimum hours between trigger firings")
    is_active: bool = Field(default=True, description="Whether the trigger is active")


# ── Response schemas ──


class TriggerResponse(BaseModel):
    """A retraining trigger rule."""
    id: str
    model_name: str
    trigger_type: str
    condition: str
    threshold: float
    cooldown_hours: int
    is_active: bool
    last_fired_at: Optional[str] = None
    created_at: str


class TriggerListResponse(BaseModel):
    """List of retraining triggers."""
    triggers: list[TriggerResponse]
    total: int


class TriggerEvaluationResponse(BaseModel):
    """Result of a single trigger evaluation."""
    trigger_id: str
    fired: bool
    reason: str
    metric_value: float
    threshold: float
    evaluated_at: str


class EvaluateAllResponse(BaseModel):
    """Results of evaluating all triggers."""
    evaluations: list[TriggerEvaluationResponse]
    total: int
    fired_count: int


class TriggerHistoryResponse(BaseModel):
    """A trigger firing history entry."""
    trigger_id: str
    model_name: str
    fired_at: str
    reason: str


class TriggerHistoryListResponse(BaseModel):
    """List of trigger history entries."""
    history: list[TriggerHistoryResponse]
    total: int
