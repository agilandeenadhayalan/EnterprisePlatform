"""
Domain models for the Hyperparameter Tuner.

Represents hyperparameter searches, individual trials, and parameter spaces.
"""

from typing import Optional


class ParamSpace:
    """Definition of a single hyperparameter's search space."""

    def __init__(
        self,
        param_name: str,
        type: str,
        min: Optional[float] = None,
        max: Optional[float] = None,
        choices: Optional[list] = None,
    ):
        self.param_name = param_name
        self.type = type
        self.min = min
        self.max = max
        self.choices = choices

    def to_dict(self) -> dict:
        result = {
            "param_name": self.param_name,
            "type": self.type,
        }
        if self.min is not None:
            result["min"] = self.min
        if self.max is not None:
            result["max"] = self.max
        if self.choices is not None:
            result["choices"] = self.choices
        return result


class SearchTrial:
    """A single trial within a hyperparameter search."""

    def __init__(
        self,
        id: str,
        search_id: str,
        params: dict,
        metrics: dict,
        status: str = "completed",
        duration_seconds: float = 0.0,
    ):
        self.id = id
        self.search_id = search_id
        self.params = params
        self.metrics = metrics
        self.status = status
        self.duration_seconds = duration_seconds

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "search_id": self.search_id,
            "params": self.params,
            "metrics": self.metrics,
            "status": self.status,
            "duration_seconds": self.duration_seconds,
        }


class HyperparameterSearch:
    """A hyperparameter search session with multiple trials."""

    def __init__(
        self,
        id: str,
        model_type: str,
        search_strategy: str,
        param_space: list,
        objective_metric: str,
        status: str = "pending",
        best_trial_id: Optional[str] = None,
        created_at: str = "2024-01-15T10:00:00Z",
    ):
        self.id = id
        self.model_type = model_type
        self.search_strategy = search_strategy
        self.param_space = param_space
        self.objective_metric = objective_metric
        self.status = status
        self.best_trial_id = best_trial_id
        self.created_at = created_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "model_type": self.model_type,
            "search_strategy": self.search_strategy,
            "param_space": [
                p.to_dict() if hasattr(p, "to_dict") else p
                for p in self.param_space
            ],
            "objective_metric": self.objective_metric,
            "status": self.status,
            "best_trial_id": self.best_trial_id,
            "created_at": self.created_at,
        }
