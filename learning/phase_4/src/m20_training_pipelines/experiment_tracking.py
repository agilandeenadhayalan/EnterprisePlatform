"""
Experiment Tracking
====================

When developing ML models, you run dozens or hundreds of experiments:
different features, hyperparameters, architectures, and data splits.
Without tracking, you lose track of what worked and why.

An experiment tracker (like MLflow, Weights & Biases, or Neptune) records:
- **Parameters**: Hyperparameters and configuration (lr=0.01, layers=3)
- **Metrics**: Performance measurements (accuracy=0.92, loss=0.15)
- **Artifacts**: Files produced (model weights, plots, predictions)
- **Metadata**: Timestamps, status, run duration

This module implements an in-memory experiment tracker that simulates
MLflow's core API. In production, these records would be stored in a
database and visualized in a web UI.

Key workflow:
    tracker = ExperimentTracker()
    tracker.create_experiment("surge_prediction_v2")
    tracker.start_run("surge_prediction_v2", "baseline_lr001")
    tracker.log_param("learning_rate", 0.01)
    tracker.log_metric("train_loss", 0.45, step=1)
    tracker.log_metric("train_loss", 0.32, step=2)
    tracker.end_run()
"""

from __future__ import annotations

import time
import uuid


class ExperimentTracker:
    """In-memory experiment tracking system (simulates MLflow).

    Organizes runs into experiments. Each experiment is a logical group
    of related runs (e.g., "surge_pricing_model_v2"). Each run is a
    single training execution with its own parameters, metrics, and
    artifacts.
    """

    def __init__(self) -> None:
        self._experiments: dict[str, dict] = {}
        self._runs: dict[str, dict] = {}
        self._active_run_id: str | None = None

    def create_experiment(self, name: str, description: str = "") -> str:
        """Create a new experiment.

        Args:
            name: Unique experiment name.
            description: Optional description.

        Returns:
            The experiment name.

        Raises:
            ValueError: If an experiment with this name already exists.
        """
        if name in self._experiments:
            raise ValueError(f"Experiment {name!r} already exists")

        self._experiments[name] = {
            "name": name,
            "description": description,
            "created_at": time.time(),
            "run_ids": [],
        }
        return name

    def start_run(self, experiment_name: str, run_name: str) -> str:
        """Start a new run within an experiment.

        Args:
            experiment_name: Name of the parent experiment.
            run_name: Human-readable name for this run.

        Returns:
            The unique run_id.

        Raises:
            KeyError: If the experiment doesn't exist.
            RuntimeError: If another run is already active.
        """
        if experiment_name not in self._experiments:
            raise KeyError(f"Experiment {experiment_name!r} not found")
        if self._active_run_id is not None:
            raise RuntimeError(
                f"Run {self._active_run_id!r} is already active. "
                f"Call end_run() first."
            )

        run_id = str(uuid.uuid4())[:8]
        self._runs[run_id] = {
            "run_id": run_id,
            "run_name": run_name,
            "experiment_name": experiment_name,
            "status": "RUNNING",
            "start_time": time.time(),
            "end_time": None,
            "params": {},
            "metrics": {},
            "artifacts": {},
        }
        self._experiments[experiment_name]["run_ids"].append(run_id)
        self._active_run_id = run_id
        return run_id

    def log_param(self, key: str, value) -> None:
        """Log a parameter for the active run.

        Parameters are configuration values that don't change during
        training (e.g., learning_rate, batch_size, model_type).

        Raises:
            RuntimeError: If no run is active.
        """
        if self._active_run_id is None:
            raise RuntimeError("No active run. Call start_run() first.")
        self._runs[self._active_run_id]["params"][key] = value

    def log_metric(self, key: str, value: float, step: int | None = None) -> None:
        """Log a metric value for the active run.

        Metrics can be logged multiple times (e.g., loss at each epoch).
        Each log creates a (value, step, timestamp) entry.

        Args:
            key: Metric name (e.g., 'train_loss', 'val_accuracy').
            value: Metric value.
            step: Optional step number (e.g., epoch number).

        Raises:
            RuntimeError: If no run is active.
        """
        if self._active_run_id is None:
            raise RuntimeError("No active run. Call start_run() first.")

        run = self._runs[self._active_run_id]
        if key not in run["metrics"]:
            run["metrics"][key] = []
        run["metrics"][key].append({
            "value": value,
            "step": step,
            "timestamp": time.time(),
        })

    def log_artifact(self, name: str, content: str) -> None:
        """Log an artifact (file content) for the active run.

        In a real system, this would save files (model weights, plots,
        predictions). Here we store content as strings.

        Raises:
            RuntimeError: If no run is active.
        """
        if self._active_run_id is None:
            raise RuntimeError("No active run. Call start_run() first.")
        self._runs[self._active_run_id]["artifacts"][name] = {
            "content": content,
            "logged_at": time.time(),
        }

    def end_run(self, status: str = "FINISHED") -> None:
        """End the active run.

        Args:
            status: Final status ('FINISHED', 'FAILED', 'KILLED').

        Raises:
            RuntimeError: If no run is active.
        """
        if self._active_run_id is None:
            raise RuntimeError("No active run to end.")

        valid_statuses = ("FINISHED", "FAILED", "KILLED")
        if status not in valid_statuses:
            raise ValueError(f"status must be one of {valid_statuses}")

        run = self._runs[self._active_run_id]
        run["status"] = status
        run["end_time"] = time.time()
        self._active_run_id = None

    def get_experiment(self, name: str) -> dict:
        """Retrieve experiment details including all run IDs.

        Raises:
            KeyError: If the experiment doesn't exist.
        """
        if name not in self._experiments:
            raise KeyError(f"Experiment {name!r} not found")
        return dict(self._experiments[name])

    def get_run(self, run_id: str) -> dict:
        """Retrieve full details of a specific run.

        Raises:
            KeyError: If the run_id doesn't exist.
        """
        if run_id not in self._runs:
            raise KeyError(f"Run {run_id!r} not found")
        return dict(self._runs[run_id])

    def compare_runs(self, run_ids: list[str], metric_key: str) -> list[dict]:
        """Compare multiple runs on a specific metric.

        Returns the latest value of the specified metric for each run,
        sorted by metric value (ascending -- best first for losses).

        Args:
            run_ids: List of run IDs to compare.
            metric_key: Name of the metric to compare.

        Returns:
            List of dicts with 'run_id', 'run_name', 'params', and
            'metric_value', sorted by metric_value ascending.
        """
        comparisons = []
        for run_id in run_ids:
            if run_id not in self._runs:
                continue
            run = self._runs[run_id]
            metric_entries = run["metrics"].get(metric_key, [])
            metric_value = metric_entries[-1]["value"] if metric_entries else None

            comparisons.append({
                "run_id": run_id,
                "run_name": run["run_name"],
                "params": dict(run["params"]),
                "metric_value": metric_value,
            })

        # Sort by metric value (None values go to end)
        comparisons.sort(
            key=lambda x: (x["metric_value"] is None, x["metric_value"] or 0)
        )
        return comparisons

    @property
    def active_run_id(self) -> str | None:
        """Return the currently active run ID, or None."""
        return self._active_run_id
