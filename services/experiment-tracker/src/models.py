"""
Domain models for the Experiment Tracker.

Represents experiments, runs, and metric comparisons across runs.
"""

from typing import Optional


class Experiment:
    """An ML experiment grouping related runs."""

    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        created_at: str = "2024-01-15T10:00:00Z",
    ):
        self.id = id
        self.name = name
        self.description = description
        self.created_at = created_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
        }


class ExperimentRun:
    """A single run within an experiment."""

    def __init__(
        self,
        id: str,
        experiment_id: str,
        run_name: str,
        params: dict,
        metrics: dict,
        artifacts: list[str],
        status: str = "completed",
        start_time: str = "2024-01-15T10:00:00Z",
        end_time: Optional[str] = None,
    ):
        self.id = id
        self.experiment_id = experiment_id
        self.run_name = run_name
        self.params = params
        self.metrics = metrics
        self.artifacts = artifacts
        self.status = status
        self.start_time = start_time
        self.end_time = end_time

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "experiment_id": self.experiment_id,
            "run_name": self.run_name,
            "params": self.params,
            "metrics": self.metrics,
            "artifacts": self.artifacts,
            "status": self.status,
            "start_time": self.start_time,
            "end_time": self.end_time,
        }


class MetricComparison:
    """Comparison of a metric across multiple runs."""

    def __init__(
        self,
        metric_name: str,
        runs: list[dict],
    ):
        self.metric_name = metric_name
        self.runs = runs

    def to_dict(self) -> dict:
        return {
            "metric_name": self.metric_name,
            "runs": self.runs,
        }
