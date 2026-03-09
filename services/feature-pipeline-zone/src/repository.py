"""
In-memory repository for the Zone Feature Pipeline service with pre-seeded data.
"""

import uuid

from models import ZoneFeatureSet


ZONE_FEATURE_CATALOG = [
    {"name": "zone_demand_last_hour", "description": "Number of ride requests in zone in last hour", "value_type": "int", "source": "rides-db"},
    {"name": "zone_avg_fare", "description": "Average fare for rides starting in zone", "value_type": "float", "source": "rides-db"},
    {"name": "zone_avg_wait_time", "description": "Average wait time for riders in zone (seconds)", "value_type": "float", "source": "rides-db"},
    {"name": "zone_supply_density", "description": "Number of available drivers per sq km in zone", "value_type": "float", "source": "driver-location"},
    {"name": "zone_surge_factor", "description": "Current surge pricing multiplier for zone", "value_type": "float", "source": "pricing-engine"},
    {"name": "zone_completed_trips", "description": "Number of completed trips in the zone in last hour", "value_type": "int", "source": "rides-db"},
    {"name": "zone_avg_trip_distance", "description": "Average trip distance in km from this zone", "value_type": "float", "source": "rides-db"},
    {"name": "zone_cancellation_rate", "description": "Cancellation rate for rides in this zone", "value_type": "float", "source": "rides-db"},
]


class ZonePipelineRepository:
    """In-memory store for zone feature pipeline."""

    def __init__(self, seed: bool = False):
        self.feature_sets: list[ZoneFeatureSet] = []
        self.runs: list[dict] = []
        if seed:
            self._seed()

    def _seed(self):
        import random
        random.seed(42)

        zones = [f"zone_{chr(65 + i // 5)}{(i % 5) + 1}" for i in range(20)]
        # 24 hours of data
        for hour_num in range(0, 24):
            hour_str = f"2026-03-09T{hour_num:02d}:00:00Z"
            for zone_id in zones:
                # Demand varies by hour (peak vs off-peak)
                is_peak = 7 <= hour_num <= 9 or 17 <= hour_num <= 19
                base_demand = random.randint(30, 80) if is_peak else random.randint(5, 30)

                features = {
                    "zone_demand_last_hour": base_demand,
                    "zone_avg_fare": round(random.uniform(8.0, 35.0), 2),
                    "zone_avg_wait_time": round(random.uniform(60, 600), 1),
                    "zone_supply_density": round(random.uniform(0.5, 10.0), 1),
                    "zone_surge_factor": round(random.uniform(1.0, 3.0), 2) if is_peak else 1.0,
                    "zone_completed_trips": max(0, base_demand - random.randint(0, 10)),
                    "zone_avg_trip_distance": round(random.uniform(2.0, 20.0), 1),
                    "zone_cancellation_rate": round(random.uniform(0.02, 0.15), 3),
                }
                self.feature_sets.append(
                    ZoneFeatureSet(
                        zone_id=zone_id,
                        hour=hour_str,
                        features=features,
                        computed_at=hour_str,
                    )
                )

    # ── Pipeline ──

    def run_pipeline(self, zone_ids: list[str] | None = None) -> dict:
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        targets = zone_ids or list({fs.zone_id for fs in self.feature_sets})
        run = {
            "id": run_id,
            "status": "completed",
            "start_time": "2026-03-09T12:00:00Z",
            "end_time": "2026-03-09T12:04:30Z",
            "features_computed": len(targets) * len(ZONE_FEATURE_CATALOG),
        }
        self.runs.append(run)
        return run

    # ── Features ──

    def get_features(self, zone_id: str) -> ZoneFeatureSet | None:
        """Get the latest features for a zone."""
        matches = [fs for fs in self.feature_sets if fs.zone_id == zone_id]
        return matches[-1] if matches else None

    def get_timeseries(self, zone_id: str, start_hour: str | None = None, end_hour: str | None = None) -> list[ZoneFeatureSet]:
        """Get zone features over time."""
        results = [fs for fs in self.feature_sets if fs.zone_id == zone_id]
        if start_hour:
            results = [fs for fs in results if fs.hour >= start_hour]
        if end_hour:
            results = [fs for fs in results if fs.hour <= end_hour]
        return results

    # ── Catalog ──

    def get_catalog(self) -> list[dict]:
        return ZONE_FEATURE_CATALOG


REPO_CLASS = ZonePipelineRepository
repo = ZonePipelineRepository(seed=True)
