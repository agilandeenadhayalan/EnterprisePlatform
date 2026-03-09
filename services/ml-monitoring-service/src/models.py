"""
Domain models for the ML Monitoring service.
"""

import uuid


class DriftResult:
    """Result of a drift detection analysis on a single feature."""

    def __init__(
        self,
        feature_name: str,
        drift_type: str,
        metric_name: str,
        metric_value: float,
        threshold: float,
        is_drifted: bool,
        id: str | None = None,
        detected_at: str = "2026-03-09T12:00:00Z",
    ):
        self.id = id or str(uuid.uuid4())
        self.feature_name = feature_name
        self.drift_type = drift_type
        self.metric_name = metric_name
        self.metric_value = metric_value
        self.threshold = threshold
        self.is_drifted = is_drifted
        self.detected_at = detected_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "feature_name": self.feature_name,
            "drift_type": self.drift_type,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "threshold": self.threshold,
            "is_drifted": self.is_drifted,
            "detected_at": self.detected_at,
        }


class ReferenceDistribution:
    """Reference distribution for a feature used in drift detection."""

    def __init__(
        self,
        feature_name: str,
        values: list[float],
        mean: float | None = None,
        std: float | None = None,
        num_bins: int = 10,
        set_at: str = "2026-03-01T00:00:00Z",
    ):
        self.feature_name = feature_name
        self.values = values
        self.mean = mean if mean is not None else (sum(values) / len(values) if values else 0.0)
        self.std = std if std is not None else self._compute_std(values, self.mean)
        self.num_bins = num_bins
        self.set_at = set_at

    @staticmethod
    def _compute_std(values: list[float], mean: float) -> float:
        if len(values) < 2:
            return 0.0
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        return variance ** 0.5

    def to_dict(self) -> dict:
        return {
            "feature_name": self.feature_name,
            "values": self.values,
            "mean": self.mean,
            "std": self.std,
            "num_bins": self.num_bins,
            "set_at": self.set_at,
        }


class DriftAlert:
    """Alert raised when drift is detected."""

    def __init__(
        self,
        feature_name: str,
        drift_type: str,
        severity: str,
        message: str,
        id: str | None = None,
        created_at: str = "2026-03-09T12:00:00Z",
    ):
        self.id = id or str(uuid.uuid4())
        self.feature_name = feature_name
        self.drift_type = drift_type
        self.severity = severity
        self.message = message
        self.created_at = created_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "feature_name": self.feature_name,
            "drift_type": self.drift_type,
            "severity": self.severity,
            "message": self.message,
            "created_at": self.created_at,
        }


class ConceptDriftResult:
    """Result of concept drift analysis on model predictions."""

    def __init__(
        self,
        model_name: str,
        error_mean: float,
        error_trend: float,
        is_drifted: bool,
    ):
        self.model_name = model_name
        self.error_mean = error_mean
        self.error_trend = error_trend
        self.is_drifted = is_drifted

    def to_dict(self) -> dict:
        return {
            "model_name": self.model_name,
            "error_mean": self.error_mean,
            "error_trend": self.error_trend,
            "is_drifted": self.is_drifted,
        }
