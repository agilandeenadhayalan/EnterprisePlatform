"""
Domain models for the Training Data Service.

Represents dataset specifications, statistics, and train/val/test splits.
"""

from typing import Optional


class DatasetSpec:
    """Specification for a training dataset."""

    def __init__(
        self,
        id: str,
        name: str,
        feature_names: list[str],
        label_column: str,
        date_range: dict,
        split_ratio: dict,
        sampling_strategy: str,
        status: str = "draft",
        created_at: str = "2024-01-15T10:00:00Z",
    ):
        self.id = id
        self.name = name
        self.feature_names = feature_names
        self.label_column = label_column
        self.date_range = date_range
        self.split_ratio = split_ratio
        self.sampling_strategy = sampling_strategy
        self.status = status
        self.created_at = created_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "feature_names": self.feature_names,
            "label_column": self.label_column,
            "date_range": self.date_range,
            "split_ratio": self.split_ratio,
            "sampling_strategy": self.sampling_strategy,
            "status": self.status,
            "created_at": self.created_at,
        }


class DatasetStats:
    """Statistical summary of a materialized dataset."""

    def __init__(
        self,
        row_count: int,
        feature_count: int,
        label_distribution: dict,
        missing_values_pct: float,
    ):
        self.row_count = row_count
        self.feature_count = feature_count
        self.label_distribution = label_distribution
        self.missing_values_pct = missing_values_pct

    def to_dict(self) -> dict:
        return {
            "row_count": self.row_count,
            "feature_count": self.feature_count,
            "label_distribution": self.label_distribution,
            "missing_values_pct": self.missing_values_pct,
        }


class DataSplit:
    """Train/validation/test split sizes."""

    def __init__(
        self,
        train_size: int,
        val_size: int,
        test_size: int,
    ):
        self.train_size = train_size
        self.val_size = val_size
        self.test_size = test_size

    def to_dict(self) -> dict:
        return {
            "train_size": self.train_size,
            "val_size": self.val_size,
            "test_size": self.test_size,
        }
