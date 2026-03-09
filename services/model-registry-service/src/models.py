"""
Domain models for the model registry service.

Represents registered models, model versions, and stage transitions.
"""

from datetime import datetime, timezone
from typing import Optional


class ModelVersion:
    """A specific version of a registered model."""

    def __init__(
        self,
        version: int,
        model_name: str,
        stage: str = "none",
        run_id: Optional[str] = None,
        metrics: Optional[dict] = None,
        hyperparameters: Optional[dict] = None,
        created_at: Optional[str] = None,
        transitioned_at: Optional[str] = None,
    ):
        self.version = version
        self.model_name = model_name
        self.stage = stage
        self.run_id = run_id
        self.metrics = metrics or {}
        self.hyperparameters = hyperparameters or {}
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.transitioned_at = transitioned_at

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "model_name": self.model_name,
            "stage": self.stage,
            "run_id": self.run_id,
            "metrics": self.metrics,
            "hyperparameters": self.hyperparameters,
            "created_at": self.created_at,
            "transitioned_at": self.transitioned_at,
        }


class RegisteredModel:
    """A registered model with its versions."""

    def __init__(
        self,
        name: str,
        description: str = "",
        model_type: str = "sklearn",
        task_type: str = "regression",
        created_at: Optional[str] = None,
    ):
        self.name = name
        self.description = description
        self.model_type = model_type
        self.task_type = task_type
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.versions: list[ModelVersion] = []

    @property
    def latest_version(self) -> Optional[int]:
        if not self.versions:
            return None
        return max(v.version for v in self.versions)

    @property
    def production_version(self) -> Optional[int]:
        for v in self.versions:
            if v.stage == "production":
                return v.version
        return None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "model_type": self.model_type,
            "task_type": self.task_type,
            "latest_version": self.latest_version,
            "production_version": self.production_version,
            "created_at": self.created_at,
        }


class StageTransition:
    """Record of a stage transition for a model version."""

    def __init__(self, from_stage: str, to_stage: str, reason: str = ""):
        self.from_stage = from_stage
        self.to_stage = to_stage
        self.reason = reason

    def to_dict(self) -> dict:
        return {
            "from_stage": self.from_stage,
            "to_stage": self.to_stage,
            "reason": self.reason,
        }
