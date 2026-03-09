"""
Domain models for the Prediction Logger service.
"""

import uuid


class PredictionLog:
    """A logged prediction with features, result, and metadata."""

    def __init__(
        self,
        model_name: str,
        model_version: str,
        features: dict,
        prediction: float,
        confidence: float,
        latency_ms: float,
        id: str | None = None,
        request_source: str = "api",
        timestamp: str = "2026-03-09T12:00:00Z",
    ):
        self.id = id or str(uuid.uuid4())
        self.model_name = model_name
        self.model_version = model_version
        self.features = features
        self.prediction = prediction
        self.confidence = confidence
        self.latency_ms = latency_ms
        self.request_source = request_source
        self.timestamp = timestamp

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "features": self.features,
            "prediction": self.prediction,
            "confidence": self.confidence,
            "latency_ms": self.latency_ms,
            "request_source": self.request_source,
            "timestamp": self.timestamp,
        }


class PredictionStats:
    """Aggregated statistics for predictions by model."""

    def __init__(
        self,
        model_name: str,
        total_predictions: int,
        avg_confidence: float,
        avg_latency_ms: float,
        predictions_today: int,
        predictions_this_hour: int,
    ):
        self.model_name = model_name
        self.total_predictions = total_predictions
        self.avg_confidence = avg_confidence
        self.avg_latency_ms = avg_latency_ms
        self.predictions_today = predictions_today
        self.predictions_this_hour = predictions_this_hour

    def to_dict(self) -> dict:
        return {
            "model_name": self.model_name,
            "total_predictions": self.total_predictions,
            "avg_confidence": self.avg_confidence,
            "avg_latency_ms": self.avg_latency_ms,
            "predictions_today": self.predictions_today,
            "predictions_this_hour": self.predictions_this_hour,
        }
