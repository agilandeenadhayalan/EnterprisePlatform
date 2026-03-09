"""
In-memory prediction logger repository with pre-seeded data.
"""

import random
import uuid
from models import PredictionLog, PredictionStats


class PredictionLoggerRepository:
    """In-memory store for prediction logs."""

    def __init__(self, seed: bool = False):
        self.logs: list[PredictionLog] = []
        if seed:
            self._seed()

    def _seed(self):
        rng = random.Random(42)
        models = [
            ("fare_predictor", "1.2.0"),
            ("eta_predictor", "2.0.1"),
            ("demand_predictor", "1.0.3"),
        ]
        days = ["2026-03-03", "2026-03-04", "2026-03-05", "2026-03-06",
                "2026-03-07", "2026-03-08", "2026-03-09"]

        # ~200 predictions across 3 models over 7 days
        count = 0
        for day in days:
            n_per_day = rng.randint(25, 35)
            for _ in range(n_per_day):
                model_name, model_version = rng.choice(models)
                hour = rng.randint(6, 23)
                minute = rng.randint(0, 59)

                if model_name == "fare_predictor":
                    features = {
                        "trip_distance": round(rng.gauss(5.0, 2.5), 2),
                        "pickup_zone": f"zone_{rng.randint(1, 20)}",
                        "hour": hour,
                    }
                    prediction = round(rng.gauss(15.0, 5.0), 2)
                    confidence = round(rng.uniform(0.75, 0.98), 3)
                    latency = round(rng.gauss(25.0, 8.0), 1)
                elif model_name == "eta_predictor":
                    features = {
                        "distance_km": round(rng.gauss(8.0, 3.0), 2),
                        "traffic_level": rng.choice(["low", "medium", "high"]),
                        "hour": hour,
                    }
                    prediction = round(rng.gauss(12.0, 4.0), 2)
                    confidence = round(rng.uniform(0.70, 0.95), 3)
                    latency = round(rng.gauss(15.0, 5.0), 1)
                else:
                    features = {
                        "zone_id": f"zone_{rng.randint(1, 20)}",
                        "day_of_week": rng.randint(0, 6),
                        "hour": hour,
                    }
                    prediction = round(rng.gauss(50.0, 20.0), 2)
                    confidence = round(rng.uniform(0.60, 0.92), 3)
                    latency = round(rng.gauss(30.0, 10.0), 1)

                latency = max(1.0, latency)
                self.logs.append(PredictionLog(
                    model_name=model_name,
                    model_version=model_version,
                    features=features,
                    prediction=prediction,
                    confidence=confidence,
                    latency_ms=latency,
                    id=f"plog-{count:04d}",
                    request_source=rng.choice(["api", "batch", "stream"]),
                    timestamp=f"{day}T{hour:02d}:{minute:02d}:00Z",
                ))
                count += 1

    # ── Log ──

    def log_prediction(self, data: dict) -> PredictionLog:
        log_entry = PredictionLog(**data)
        self.logs.append(log_entry)
        return log_entry

    def log_batch(self, items: list[dict]) -> int:
        for item in items:
            self.log_prediction(item)
        return len(items)

    # ── Query ──

    def query_logs(self, model: str | None = None, date_from: str | None = None,
                   date_to: str | None = None, limit: int = 50) -> list[PredictionLog]:
        results = self.logs
        if model:
            results = [r for r in results if r.model_name == model]
        if date_from:
            results = [r for r in results if r.timestamp >= date_from]
        if date_to:
            results = [r for r in results if r.timestamp <= date_to]
        return results[:limit]

    def get_by_id(self, log_id: str) -> PredictionLog | None:
        for log in self.logs:
            if log.id == log_id:
                return log
        return None

    # ── Stats ──

    def get_stats(self) -> list[PredictionStats]:
        model_names = sorted({l.model_name for l in self.logs})
        result = []
        today = "2026-03-09"
        current_hour = "2026-03-09T12"

        for model in model_names:
            model_logs = [l for l in self.logs if l.model_name == model]
            total = len(model_logs)
            avg_conf = round(sum(l.confidence for l in model_logs) / total, 4) if total else 0.0
            avg_lat = round(sum(l.latency_ms for l in model_logs) / total, 2) if total else 0.0
            today_count = sum(1 for l in model_logs if l.timestamp.startswith(today))
            hour_count = sum(1 for l in model_logs if l.timestamp.startswith(current_hour))

            result.append(PredictionStats(
                model_name=model,
                total_predictions=total,
                avg_confidence=avg_conf,
                avg_latency_ms=avg_lat,
                predictions_today=today_count,
                predictions_this_hour=hour_count,
            ))
        return result


REPO_CLASS = PredictionLoggerRepository
repo = PredictionLoggerRepository(seed=True)
