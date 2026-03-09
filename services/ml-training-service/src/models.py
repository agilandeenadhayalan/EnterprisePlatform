"""
Domain models for the ML Training Service.

Represents training jobs, model architectures, and training metrics.
"""

from typing import Optional


class TrainingMetrics:
    """Metrics captured during a single training epoch."""

    def __init__(
        self,
        epoch: int,
        train_loss: float,
        val_loss: float,
        train_metric: float,
        val_metric: float,
    ):
        self.epoch = epoch
        self.train_loss = train_loss
        self.val_loss = val_loss
        self.train_metric = train_metric
        self.val_metric = val_metric

    def to_dict(self) -> dict:
        return {
            "epoch": self.epoch,
            "train_loss": self.train_loss,
            "val_loss": self.val_loss,
            "train_metric": self.train_metric,
            "val_metric": self.val_metric,
        }


class TrainingJob:
    """A model training job with lifecycle tracking."""

    def __init__(
        self,
        id: str,
        model_type: str,
        hyperparameters: dict,
        dataset_id: str,
        status: str = "pending",
        metrics: Optional[list] = None,
        created_at: str = "2024-01-15T10:00:00Z",
        started_at: Optional[str] = None,
        completed_at: Optional[str] = None,
        logs: Optional[list] = None,
    ):
        self.id = id
        self.model_type = model_type
        self.hyperparameters = hyperparameters
        self.dataset_id = dataset_id
        self.status = status
        self.metrics = metrics or []
        self.created_at = created_at
        self.started_at = started_at
        self.completed_at = completed_at
        self.logs = logs or []

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "model_type": self.model_type,
            "hyperparameters": self.hyperparameters,
            "dataset_id": self.dataset_id,
            "status": self.status,
            "metrics": [m.to_dict() if hasattr(m, "to_dict") else m for m in self.metrics],
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "logs": self.logs,
        }


class ModelArchitecture:
    """A registered model architecture available for training."""

    def __init__(
        self,
        name: str,
        type: str,
        description: str,
        default_hyperparameters: dict,
    ):
        self.name = name
        self.type = type
        self.description = description
        self.default_hyperparameters = default_hyperparameters

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "default_hyperparameters": self.default_hyperparameters,
        }
