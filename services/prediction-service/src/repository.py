"""
Prediction repository — in-memory model store and prediction engine.

Pre-seeds with 3 loaded models: fare_predictor, demand_predictor, eta_predictor.
Each model has a simple formula-based prediction function for demonstration.
"""

import time
import random
from typing import Optional

from models import LoadedModel, PredictionResult


def _predict_fare(features: dict) -> tuple[float, float]:
    """Fare prediction: base_fare + distance*per_mile + duration*per_min."""
    base_fare = 3.50
    distance = features.get("distance_miles", 5.0)
    duration = features.get("duration_minutes", 15.0)
    surge = features.get("surge_multiplier", 1.0)
    fare = (base_fare + distance * 2.15 + duration * 0.35) * surge
    confidence = min(0.95, 0.80 + 0.01 * min(distance, 15))
    return round(fare, 2), round(confidence, 4)


def _predict_demand(features: dict) -> tuple[float, float]:
    """Demand prediction: rides per hour in a zone."""
    hour = features.get("hour", 12)
    zone_population = features.get("zone_population", 50000)
    is_weekend = features.get("is_weekend", False)
    base = zone_population / 5000
    hour_factor = 1.0 + 0.5 * (1.0 - abs(hour - 17) / 12.0)
    weekend_factor = 0.7 if is_weekend else 1.0
    demand = base * hour_factor * weekend_factor
    confidence = 0.72 + 0.02 * min(hour_factor, 5)
    return round(demand, 2), round(min(confidence, 0.92), 4)


def _predict_eta(features: dict) -> tuple[float, float]:
    """ETA prediction: estimated time of arrival in minutes."""
    distance = features.get("distance_miles", 3.0)
    traffic_level = features.get("traffic_level", 0.5)
    time_of_day = features.get("hour", 12)
    base_speed = 25.0  # mph
    traffic_factor = 1.0 + traffic_level * 1.5
    eta = (distance / base_speed) * 60 * traffic_factor
    confidence = max(0.60, 0.88 - traffic_level * 0.2)
    return round(eta, 2), round(confidence, 4)


_PREDICTORS = {
    "fare_predictor": _predict_fare,
    "demand_predictor": _predict_demand,
    "eta_predictor": _predict_eta,
}


class PredictionRepository:
    """In-memory model store with prediction capabilities."""

    def __init__(self, seed: bool = True):
        self._models: dict[str, LoadedModel] = {}
        self._rng = random.Random(42)
        if seed:
            self._seed()

    def _seed(self):
        """Pre-seed with 3 loaded models."""
        self._models["fare_predictor"] = LoadedModel(
            name="fare_predictor",
            version="2.1.0",
            loaded_at="2024-01-15T10:00:00+00:00",
            request_count=1250,
            avg_latency_ms=4.2,
            total_predictions=3800,
        )
        self._models["demand_predictor"] = LoadedModel(
            name="demand_predictor",
            version="1.3.0",
            loaded_at="2024-01-15T10:00:00+00:00",
            request_count=890,
            avg_latency_ms=6.8,
            total_predictions=890,
        )
        self._models["eta_predictor"] = LoadedModel(
            name="eta_predictor",
            version="3.0.1",
            loaded_at="2024-01-15T10:00:00+00:00",
            request_count=2100,
            avg_latency_ms=3.5,
            total_predictions=6500,
        )

    def list_models(self) -> list[LoadedModel]:
        """List all loaded models."""
        return list(self._models.values())

    def get_model(self, name: str) -> Optional[LoadedModel]:
        """Get a loaded model by name."""
        return self._models.get(name)

    def load_model(self, name: str, version: Optional[str] = None) -> LoadedModel:
        """Load or reload a model. Returns the loaded model."""
        v = version or "1.0.0"
        if name in self._models and version is None:
            # Reload existing — bump version patch
            existing = self._models[name]
            parts = existing.version.split(".")
            parts[-1] = str(int(parts[-1]) + 1)
            v = ".".join(parts)
        from datetime import datetime, timezone
        model = LoadedModel(name=name, version=v)
        self._models[name] = model
        return model

    def predict(self, model_name: str, features: dict) -> PredictionResult:
        """Run a single prediction."""
        model = self._models.get(model_name)
        if model is None:
            raise KeyError(f"Model '{model_name}' is not loaded")

        start = time.perf_counter()
        predictor = _PREDICTORS.get(model_name)
        if predictor:
            prediction, confidence = predictor(features)
        else:
            # Generic fallback for unknown models
            prediction = sum(float(v) for v in features.values() if isinstance(v, (int, float))) * 0.1
            confidence = 0.50
            prediction = round(prediction, 2)

        latency_ms = round((time.perf_counter() - start) * 1000, 3)
        # Ensure minimum measurable latency for realism
        latency_ms = max(latency_ms, 0.1)
        model.record_latency(latency_ms)

        return PredictionResult(
            prediction=prediction,
            confidence=confidence,
            model_name=model_name,
            model_version=model.version,
            latency_ms=latency_ms,
        )

    def predict_batch(self, model_name: str, instances: list[dict]) -> list[PredictionResult]:
        """Run batch predictions."""
        return [self.predict(model_name, features) for features in instances]

    def get_latency_stats(self) -> dict:
        """Get latency statistics across all models."""
        models = self.list_models()
        total_requests = sum(m.request_count for m in models)
        if total_requests > 0:
            weighted_latency = sum(m.avg_latency_ms * m.request_count for m in models)
            overall_avg = round(weighted_latency / total_requests, 3)
        else:
            overall_avg = 0.0
        return {
            "models": models,
            "overall_avg_latency_ms": overall_avg,
            "total_requests": total_requests,
        }


repo = PredictionRepository(seed=True)
