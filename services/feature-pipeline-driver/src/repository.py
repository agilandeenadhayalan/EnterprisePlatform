"""
In-memory repository for the Driver Feature Pipeline service with pre-seeded data.
"""

import uuid

from models import DriverFeatureSet, PipelineRun


DRIVER_FEATURE_CATALOG = [
    {"name": "driver_avg_rating", "description": "Average driver rating over all trips", "value_type": "float", "source": "rides-db"},
    {"name": "driver_total_trips_30d", "description": "Total trips completed in last 30 days", "value_type": "int", "source": "rides-db"},
    {"name": "driver_earnings_per_hour", "description": "Average earnings per online hour", "value_type": "float", "source": "payments-db"},
    {"name": "driver_acceptance_rate", "description": "Rate of accepted ride requests", "value_type": "float", "source": "rides-db"},
    {"name": "driver_cancel_rate", "description": "Rate of cancelled rides after acceptance", "value_type": "float", "source": "rides-db"},
    {"name": "driver_online_hours_7d", "description": "Total online hours in last 7 days", "value_type": "float", "source": "driver-sessions"},
    {"name": "driver_peak_hour_pct", "description": "Percentage of trips during peak hours", "value_type": "float", "source": "rides-db"},
    {"name": "driver_avg_trip_distance", "description": "Average trip distance in km", "value_type": "float", "source": "rides-db"},
]


class DriverPipelineRepository:
    """In-memory store for driver feature pipeline."""

    def __init__(self, seed: bool = False):
        self.feature_sets: dict[str, DriverFeatureSet] = {}
        self.runs: list[PipelineRun] = []
        if seed:
            self._seed()

    def _seed(self):
        import random
        random.seed(42)
        for i in range(1, 16):
            driver_id = f"driver_{i:03d}"
            features = {
                "driver_avg_rating": round(random.uniform(3.5, 5.0), 2),
                "driver_total_trips_30d": random.randint(20, 200),
                "driver_earnings_per_hour": round(random.uniform(15.0, 40.0), 2),
                "driver_acceptance_rate": round(random.uniform(0.7, 0.99), 2),
                "driver_cancel_rate": round(random.uniform(0.01, 0.15), 2),
                "driver_online_hours_7d": round(random.uniform(10, 60), 1),
                "driver_peak_hour_pct": round(random.uniform(0.2, 0.8), 2),
                "driver_avg_trip_distance": round(random.uniform(3.0, 25.0), 1),
            }
            self.feature_sets[driver_id] = DriverFeatureSet(
                driver_id=driver_id, features=features, computed_at="2026-03-09T10:00:00Z",
            )

        self.runs = [
            PipelineRun("run_001", "completed", "2026-03-09T08:00:00Z", "2026-03-09T08:05:32Z", 120),
            PipelineRun("run_002", "completed", "2026-03-09T09:00:00Z", "2026-03-09T09:04:18Z", 120),
            PipelineRun("run_003", "completed", "2026-03-09T10:00:00Z", "2026-03-09T10:05:01Z", 120),
        ]

    # ── Pipeline ──

    def run_pipeline(self, driver_ids: list[str] | None = None) -> PipelineRun:
        import random
        random.seed(None)
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        targets = driver_ids or list(self.feature_sets.keys())
        run = PipelineRun(
            id=run_id,
            status="completed",
            start_time="2026-03-09T12:00:00Z",
            end_time="2026-03-09T12:03:45Z",
            features_computed=len(targets) * len(DRIVER_FEATURE_CATALOG),
        )
        self.runs.append(run)

        for did in targets:
            if did not in self.feature_sets:
                features = {
                    "driver_avg_rating": round(random.uniform(3.5, 5.0), 2),
                    "driver_total_trips_30d": random.randint(20, 200),
                    "driver_earnings_per_hour": round(random.uniform(15.0, 40.0), 2),
                    "driver_acceptance_rate": round(random.uniform(0.7, 0.99), 2),
                    "driver_cancel_rate": round(random.uniform(0.01, 0.15), 2),
                    "driver_online_hours_7d": round(random.uniform(10, 60), 1),
                    "driver_peak_hour_pct": round(random.uniform(0.2, 0.8), 2),
                    "driver_avg_trip_distance": round(random.uniform(3.0, 25.0), 1),
                }
                self.feature_sets[did] = DriverFeatureSet(
                    driver_id=did, features=features, computed_at="2026-03-09T12:03:45Z",
                )
        return run

    # ── Features ──

    def get_features(self, driver_id: str) -> DriverFeatureSet | None:
        return self.feature_sets.get(driver_id)

    def list_feature_sets(self) -> list[DriverFeatureSet]:
        return list(self.feature_sets.values())

    # ── Status ──

    def get_runs(self) -> list[PipelineRun]:
        return self.runs

    def get_catalog(self) -> list[dict]:
        return DRIVER_FEATURE_CATALOG


REPO_CLASS = DriverPipelineRepository
repo = DriverPipelineRepository(seed=True)
