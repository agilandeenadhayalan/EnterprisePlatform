"""
Domain models for the prediction service.

Represents loaded ML models, prediction requests/results, and latency tracking.
"""

from datetime import datetime, timezone
from typing import Optional


class LoadedModel:
    """An ML model currently loaded in memory and ready for inference."""

    def __init__(
        self,
        name: str,
        version: str,
        loaded_at: Optional[str] = None,
        request_count: int = 0,
        avg_latency_ms: float = 0.0,
        total_predictions: int = 0,
    ):
        self.name = name
        self.version = version
        self.loaded_at = loaded_at or datetime.now(timezone.utc).isoformat()
        self.request_count = request_count
        self.avg_latency_ms = avg_latency_ms
        self.total_predictions = total_predictions
        self._latency_sum: float = avg_latency_ms * request_count

    def record_latency(self, latency_ms: float, num_predictions: int = 1):
        """Record latency for a prediction request."""
        self._latency_sum += latency_ms
        self.request_count += 1
        self.total_predictions += num_predictions
        self.avg_latency_ms = round(self._latency_sum / self.request_count, 3)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "loaded_at": self.loaded_at,
            "request_count": self.request_count,
            "avg_latency_ms": self.avg_latency_ms,
            "total_predictions": self.total_predictions,
        }


class PredictionResult:
    """A single prediction output."""

    def __init__(
        self,
        prediction: float,
        confidence: float,
        model_name: str,
        model_version: str,
        latency_ms: float,
    ):
        self.prediction = prediction
        self.confidence = confidence
        self.model_name = model_name
        self.model_version = model_version
        self.latency_ms = latency_ms

    def to_dict(self) -> dict:
        return {
            "prediction": self.prediction,
            "confidence": self.confidence,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "latency_ms": self.latency_ms,
        }
