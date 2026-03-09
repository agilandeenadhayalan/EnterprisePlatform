"""
Domain models for the batch prediction service.

Represents batch prediction jobs, their status tracking, and result records.
"""

from datetime import datetime, timezone
from typing import Optional


class BatchJob:
    """A batch prediction job that scores a dataset with a model."""

    def __init__(
        self,
        id: str,
        model_name: str,
        dataset_id: str,
        status: str = "pending",
        output_format: str = "json",
        total_records: int = 0,
        processed_records: int = 0,
        created_at: Optional[str] = None,
        completed_at: Optional[str] = None,
    ):
        self.id = id
        self.model_name = model_name
        self.dataset_id = dataset_id
        self.status = status
        self.output_format = output_format
        self.total_records = total_records
        self.processed_records = processed_records
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.completed_at = completed_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "model_name": self.model_name,
            "dataset_id": self.dataset_id,
            "status": self.status,
            "output_format": self.output_format,
            "total_records": self.total_records,
            "processed_records": self.processed_records,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


class BatchResult:
    """A single prediction result from a batch job."""

    def __init__(
        self,
        job_id: str,
        entity_id: str,
        prediction: float,
        confidence: float,
    ):
        self.job_id = job_id
        self.entity_id = entity_id
        self.prediction = prediction
        self.confidence = confidence

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "entity_id": self.entity_id,
            "prediction": self.prediction,
            "confidence": self.confidence,
        }
