"""
Domain models for the model evaluation service.

Represents evaluation results, model comparisons, and leaderboard entries.
"""

from datetime import datetime, timezone
from typing import Optional


class EvaluationResult:
    """Result of evaluating a model on a dataset."""

    def __init__(
        self,
        id: str,
        model_name: str,
        model_version: str,
        dataset_id: str,
        task_type: str = "regression",
        metrics: Optional[dict] = None,
        evaluated_at: Optional[str] = None,
    ):
        self.id = id
        self.model_name = model_name
        self.model_version = model_version
        self.dataset_id = dataset_id
        self.task_type = task_type
        self.metrics = metrics or {}
        self.evaluated_at = evaluated_at or datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "dataset_id": self.dataset_id,
            "task_type": self.task_type,
            "metrics": self.metrics,
            "evaluated_at": self.evaluated_at,
        }


class ModelComparison:
    """Comparison of two models on the same dataset."""

    def __init__(
        self,
        model_a: str,
        model_b: str,
        dataset_id: str,
        metrics_a: dict,
        metrics_b: dict,
        winner: str,
        improvement_pct: float,
    ):
        self.model_a = model_a
        self.model_b = model_b
        self.dataset_id = dataset_id
        self.metrics_a = metrics_a
        self.metrics_b = metrics_b
        self.winner = winner
        self.improvement_pct = improvement_pct

    def to_dict(self) -> dict:
        return {
            "model_a": self.model_a,
            "model_b": self.model_b,
            "dataset_id": self.dataset_id,
            "metrics_a": self.metrics_a,
            "metrics_b": self.metrics_b,
            "winner": self.winner,
            "improvement_pct": self.improvement_pct,
        }
