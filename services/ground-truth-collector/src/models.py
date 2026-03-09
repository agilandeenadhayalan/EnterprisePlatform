"""
Domain models for the Ground Truth Collector service.
"""

import uuid


class GroundTruthLabel:
    """A ground-truth label linked to a prediction."""

    def __init__(
        self,
        prediction_id: str,
        model_name: str,
        actual_value: float,
        id: str | None = None,
        label_timestamp: str = "2026-03-09T12:00:00Z",
        delay_seconds: float = 3600.0,
    ):
        self.id = id or str(uuid.uuid4())
        self.prediction_id = prediction_id
        self.model_name = model_name
        self.actual_value = actual_value
        self.label_timestamp = label_timestamp
        self.delay_seconds = delay_seconds

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "prediction_id": self.prediction_id,
            "model_name": self.model_name,
            "actual_value": self.actual_value,
            "label_timestamp": self.label_timestamp,
            "delay_seconds": self.delay_seconds,
        }


class Prediction:
    """A stored prediction waiting for ground truth."""

    def __init__(
        self,
        prediction_id: str,
        model_name: str,
        predicted_value: float,
        timestamp: str = "2026-03-09T10:00:00Z",
    ):
        self.prediction_id = prediction_id
        self.model_name = model_name
        self.predicted_value = predicted_value
        self.timestamp = timestamp

    def to_dict(self) -> dict:
        return {
            "prediction_id": self.prediction_id,
            "model_name": self.model_name,
            "predicted_value": self.predicted_value,
            "timestamp": self.timestamp,
        }


class PredictionGroundTruthPair:
    """A joined prediction with its ground truth label."""

    def __init__(
        self,
        prediction_id: str,
        predicted_value: float,
        actual_value: float,
        error: float,
        model_name: str,
    ):
        self.prediction_id = prediction_id
        self.predicted_value = predicted_value
        self.actual_value = actual_value
        self.error = error
        self.model_name = model_name

    def to_dict(self) -> dict:
        return {
            "prediction_id": self.prediction_id,
            "predicted_value": self.predicted_value,
            "actual_value": self.actual_value,
            "error": self.error,
            "model_name": self.model_name,
        }


class LabelCoverage:
    """Label coverage statistics for a model."""

    def __init__(
        self,
        model_name: str,
        total_predictions: int,
        labeled_predictions: int,
        coverage_pct: float,
    ):
        self.model_name = model_name
        self.total_predictions = total_predictions
        self.labeled_predictions = labeled_predictions
        self.coverage_pct = coverage_pct

    def to_dict(self) -> dict:
        return {
            "model_name": self.model_name,
            "total_predictions": self.total_predictions,
            "labeled_predictions": self.labeled_predictions,
            "coverage_pct": self.coverage_pct,
        }
