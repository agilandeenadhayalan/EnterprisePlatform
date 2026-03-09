"""
Training Data repository — in-memory pre-seeded dataset specifications.

Seeds dataset specs with stats and sample data for fare, demand, and ETA
training datasets. In production, this would query data lakes and feature stores.
"""

import random
import uuid
from typing import Optional

from models import DatasetSpec, DatasetStats, DataSplit


class TrainingDataRepository:
    """In-memory training data store with pre-seeded sample data."""

    def __init__(self, seed: bool = True):
        self._datasets: dict[str, DatasetSpec] = {}
        self._stats: dict[str, DatasetStats] = {}
        self._splits: dict[str, DataSplit] = {}
        self._samples: dict[str, list[dict]] = {}
        self._rng = random.Random(42)

        if seed:
            self._seed_data()

    def _seed_data(self):
        """Pre-populate with dataset specifications, stats, and samples."""
        datasets_config = [
            {
                "id": "ds-fare-v1",
                "name": "fare_training_v1",
                "feature_names": [
                    "pickup_zone_id", "dropoff_zone_id", "trip_distance",
                    "hour_of_day", "day_of_week", "passenger_count",
                    "weather_temp", "weather_precip", "is_rush_hour",
                ],
                "label_column": "fare_amount",
                "date_range": {"start": "2024-01-01", "end": "2024-01-31"},
                "split_ratio": {"train": 0.7, "val": 0.15, "test": 0.15},
                "sampling_strategy": "random",
                "status": "ready",
                "created_at": "2024-01-10T08:00:00Z",
                "row_count": 150000,
                "label_dist": {"0-10": 0.25, "10-20": 0.35, "20-40": 0.28, "40+": 0.12},
                "missing_pct": 0.8,
            },
            {
                "id": "ds-demand-v1",
                "name": "demand_training_v1",
                "feature_names": [
                    "zone_id", "hour_of_day", "day_of_week",
                    "is_holiday", "weather_temp", "weather_precip",
                    "historical_demand_1h", "historical_demand_24h",
                ],
                "label_column": "demand_count",
                "date_range": {"start": "2024-01-01", "end": "2024-01-31"},
                "split_ratio": {"train": 0.8, "val": 0.1, "test": 0.1},
                "sampling_strategy": "time_based",
                "status": "ready",
                "created_at": "2024-01-11T09:00:00Z",
                "row_count": 80000,
                "label_dist": {"low": 0.40, "medium": 0.35, "high": 0.25},
                "missing_pct": 1.2,
            },
            {
                "id": "ds-eta-v1",
                "name": "eta_training_v1",
                "feature_names": [
                    "pickup_zone_id", "dropoff_zone_id", "trip_distance",
                    "hour_of_day", "day_of_week", "traffic_speed_avg",
                    "traffic_speed_segment", "route_segment_count",
                    "weather_temp", "weather_visibility",
                ],
                "label_column": "trip_duration_minutes",
                "date_range": {"start": "2023-12-01", "end": "2024-01-31"},
                "split_ratio": {"train": 0.7, "val": 0.15, "test": 0.15},
                "sampling_strategy": "stratified",
                "status": "ready",
                "created_at": "2024-01-12T10:00:00Z",
                "row_count": 200000,
                "label_dist": {"0-10min": 0.30, "10-20min": 0.35, "20-40min": 0.25, "40+min": 0.10},
                "missing_pct": 0.5,
            },
        ]

        for cfg in datasets_config:
            row_count = cfg.pop("row_count")
            label_dist = cfg.pop("label_dist")
            missing_pct = cfg.pop("missing_pct")

            ds = DatasetSpec(
                id=cfg["id"],
                name=cfg["name"],
                feature_names=cfg["feature_names"],
                label_column=cfg["label_column"],
                date_range=cfg["date_range"],
                split_ratio=cfg["split_ratio"],
                sampling_strategy=cfg["sampling_strategy"],
                status=cfg["status"],
                created_at=cfg["created_at"],
            )
            self._datasets[ds.id] = ds

            # Stats
            self._stats[ds.id] = DatasetStats(
                row_count=row_count,
                feature_count=len(ds.feature_names),
                label_distribution=label_dist,
                missing_values_pct=missing_pct,
            )

            # Splits
            train_r = ds.split_ratio.get("train", 0.7)
            val_r = ds.split_ratio.get("val", 0.15)
            test_r = ds.split_ratio.get("test", 0.15)
            self._splits[ds.id] = DataSplit(
                train_size=int(row_count * train_r),
                val_size=int(row_count * val_r),
                test_size=int(row_count * test_r),
            )

            # Sample data
            sample_rows = []
            for i in range(5):
                row = {}
                for feat in ds.feature_names:
                    if "zone_id" in feat:
                        row[feat] = self._rng.randint(1, 265)
                    elif "hour" in feat:
                        row[feat] = self._rng.randint(0, 23)
                    elif "day" in feat:
                        row[feat] = self._rng.randint(0, 6)
                    elif "distance" in feat:
                        row[feat] = round(self._rng.uniform(0.5, 20.0), 2)
                    elif "temp" in feat:
                        row[feat] = round(self._rng.uniform(20.0, 90.0), 1)
                    elif "precip" in feat:
                        row[feat] = round(self._rng.uniform(0.0, 1.0), 2)
                    elif "speed" in feat:
                        row[feat] = round(self._rng.uniform(5.0, 45.0), 1)
                    elif "count" in feat:
                        row[feat] = self._rng.randint(1, 6)
                    elif "is_" in feat:
                        row[feat] = self._rng.choice([0, 1])
                    else:
                        row[feat] = round(self._rng.uniform(0.0, 100.0), 2)
                # Add label
                if "fare" in ds.label_column:
                    row[ds.label_column] = round(self._rng.uniform(5.0, 80.0), 2)
                elif "demand" in ds.label_column:
                    row[ds.label_column] = self._rng.randint(0, 150)
                else:
                    row[ds.label_column] = round(self._rng.uniform(3.0, 60.0), 1)
                sample_rows.append(row)

            self._samples[ds.id] = sample_rows

    # ── Dataset operations ──

    def create_dataset(
        self,
        name: str,
        feature_names: list[str],
        label_column: str,
        date_range: dict,
        split_ratio: dict,
        sampling_strategy: str,
    ) -> DatasetSpec:
        """Create a new dataset specification in draft status."""
        ds_id = f"ds-{uuid.uuid4().hex[:8]}"
        ds = DatasetSpec(
            id=ds_id,
            name=name,
            feature_names=feature_names,
            label_column=label_column,
            date_range=date_range,
            split_ratio=split_ratio,
            sampling_strategy=sampling_strategy,
            status="draft",
            created_at="2024-01-15T10:00:00Z",
        )
        self._datasets[ds_id] = ds
        return ds

    def list_datasets(self) -> list[DatasetSpec]:
        """Return all dataset specifications."""
        return list(self._datasets.values())

    def get_dataset(self, dataset_id: str) -> Optional[DatasetSpec]:
        """Return a single dataset spec by ID."""
        return self._datasets.get(dataset_id)

    def prepare_dataset(self, dataset_id: str) -> Optional[DatasetSpec]:
        """Prepare/materialize a dataset. Changes status to ready."""
        ds = self._datasets.get(dataset_id)
        if ds is None:
            return None
        ds.status = "ready"
        # Generate stats if not present
        if dataset_id not in self._stats:
            row_count = self._rng.randint(10000, 100000)
            self._stats[dataset_id] = DatasetStats(
                row_count=row_count,
                feature_count=len(ds.feature_names),
                label_distribution={"bin_1": 0.5, "bin_2": 0.5},
                missing_values_pct=round(self._rng.uniform(0.0, 5.0), 2),
            )
            train_r = ds.split_ratio.get("train", 0.7)
            val_r = ds.split_ratio.get("val", 0.15)
            test_r = ds.split_ratio.get("test", 0.15)
            self._splits[dataset_id] = DataSplit(
                train_size=int(row_count * train_r),
                val_size=int(row_count * val_r),
                test_size=int(row_count * test_r),
            )
        return ds

    def get_stats(self, dataset_id: str) -> Optional[DatasetStats]:
        """Return stats for a dataset. None if not prepared."""
        return self._stats.get(dataset_id)

    def get_split(self, dataset_id: str) -> Optional[DataSplit]:
        """Return split sizes for a dataset."""
        return self._splits.get(dataset_id)

    def get_sample(self, dataset_id: str) -> Optional[list[dict]]:
        """Return sample rows from a dataset."""
        return self._samples.get(dataset_id)


# Singleton repository instance
repo = TrainingDataRepository(seed=True)
