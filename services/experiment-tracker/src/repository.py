"""
Experiment Tracker repository — in-memory pre-seeded experiment data.

Seeds experiments with multiple runs containing params, metrics, and
artifacts. In production, this would proxy to MLflow.
"""

import random
import uuid
from typing import Optional

from models import Experiment, ExperimentRun, MetricComparison


class ExperimentRepository:
    """In-memory experiment data store with pre-seeded sample data."""

    def __init__(self, seed: bool = True):
        self._experiments: dict[str, Experiment] = {}
        self._runs: dict[str, list[ExperimentRun]] = {}
        self._all_runs: dict[str, ExperimentRun] = {}
        self._rng = random.Random(42)

        if seed:
            self._seed_data()

    def _seed_data(self):
        """Pre-populate with experiments and runs."""
        experiments_config = [
            {
                "id": "exp-001",
                "name": "fare_prediction",
                "description": "Fare prediction model experiments comparing RF, NN, and GBT approaches",
                "created_at": "2024-01-05T08:00:00Z",
                "runs": [
                    {
                        "run_name": "rf_baseline",
                        "params": {"model": "random_forest", "n_estimators": 100, "max_depth": 10},
                        "metrics": {"rmse": 3.45, "mae": 2.12, "r2": 0.87, "mape": 8.5},
                        "artifacts": ["models/fare_rf_v1.pkl", "plots/rf_feature_importance.png"],
                    },
                    {
                        "run_name": "nn_v1",
                        "params": {"model": "neural_network", "hidden_layers": "128,64", "lr": 0.001, "epochs": 50},
                        "metrics": {"rmse": 2.98, "mae": 1.85, "r2": 0.91, "mape": 7.2},
                        "artifacts": ["models/fare_nn_v1.pt", "plots/nn_loss_curve.png"],
                    },
                    {
                        "run_name": "nn_v2_tuned",
                        "params": {"model": "neural_network", "hidden_layers": "256,128,64", "lr": 0.0005, "epochs": 100},
                        "metrics": {"rmse": 2.56, "mae": 1.62, "r2": 0.93, "mape": 6.1},
                        "artifacts": ["models/fare_nn_v2.pt", "plots/nn_v2_loss_curve.png", "plots/nn_v2_predictions.png"],
                    },
                    {
                        "run_name": "gbt_v1",
                        "params": {"model": "gradient_boosting", "n_estimators": 200, "lr": 0.05},
                        "metrics": {"rmse": 2.78, "mae": 1.75, "r2": 0.92, "mape": 6.8},
                        "artifacts": ["models/fare_gbt_v1.pkl"],
                    },
                ],
            },
            {
                "id": "exp-002",
                "name": "demand_forecast",
                "description": "Zone-level demand forecasting experiments with temporal features",
                "created_at": "2024-01-08T10:00:00Z",
                "runs": [
                    {
                        "run_name": "baseline_linear",
                        "params": {"model": "linear_regression", "features": "basic"},
                        "metrics": {"rmse": 12.3, "mae": 8.7, "r2": 0.72, "mape": 15.2},
                        "artifacts": ["models/demand_lr_v1.pkl"],
                    },
                    {
                        "run_name": "gb_temporal",
                        "params": {"model": "gradient_boosting", "n_estimators": 300, "features": "temporal"},
                        "metrics": {"rmse": 7.8, "mae": 5.2, "r2": 0.88, "mape": 9.8},
                        "artifacts": ["models/demand_gb_v1.pkl", "plots/demand_predictions.png"],
                    },
                    {
                        "run_name": "lstm_v1",
                        "params": {"model": "lstm", "units": 64, "sequence_length": 24},
                        "metrics": {"rmse": 6.9, "mae": 4.5, "r2": 0.91, "mape": 8.3},
                        "artifacts": ["models/demand_lstm_v1.pt", "plots/lstm_forecast.png"],
                    },
                ],
            },
            {
                "id": "exp-003",
                "name": "eta_estimation",
                "description": "ETA prediction experiments using route and traffic features",
                "created_at": "2024-01-10T14:00:00Z",
                "runs": [
                    {
                        "run_name": "simple_avg",
                        "params": {"model": "historical_average", "lookback_days": 30},
                        "metrics": {"rmse": 5.8, "mae": 4.2, "r2": 0.65, "mape": 18.5},
                        "artifacts": [],
                    },
                    {
                        "run_name": "rf_route_features",
                        "params": {"model": "random_forest", "n_estimators": 150, "features": "route+traffic"},
                        "metrics": {"rmse": 3.2, "mae": 2.1, "r2": 0.85, "mape": 10.2},
                        "artifacts": ["models/eta_rf_v1.pkl"],
                    },
                    {
                        "run_name": "lstm_sequence",
                        "params": {"model": "lstm", "units": 128, "sequence_length": 10, "features": "route+traffic+weather"},
                        "metrics": {"rmse": 2.5, "mae": 1.7, "r2": 0.91, "mape": 7.5},
                        "artifacts": ["models/eta_lstm_v1.pt", "plots/eta_lstm_predictions.png"],
                    },
                    {
                        "run_name": "transformer_v1",
                        "params": {"model": "transformer", "heads": 4, "layers": 2, "features": "all"},
                        "metrics": {"rmse": 2.3, "mae": 1.5, "r2": 0.93, "mape": 6.8},
                        "artifacts": ["models/eta_transformer_v1.pt", "plots/eta_attention_maps.png"],
                    },
                    {
                        "run_name": "transformer_v2",
                        "params": {"model": "transformer", "heads": 8, "layers": 3, "features": "all"},
                        "metrics": {"rmse": 2.1, "mae": 1.4, "r2": 0.94, "mape": 6.2},
                        "artifacts": ["models/eta_transformer_v2.pt"],
                    },
                ],
            },
        ]

        for exp_cfg in experiments_config:
            runs_cfg = exp_cfg.pop("runs")
            exp = Experiment(**exp_cfg)
            self._experiments[exp.id] = exp
            self._runs[exp.id] = []

            for i, run_cfg in enumerate(runs_cfg):
                run_id = f"run-{exp.id[-3:]}-{i + 1:02d}"
                run = ExperimentRun(
                    id=run_id,
                    experiment_id=exp.id,
                    run_name=run_cfg["run_name"],
                    params=run_cfg["params"],
                    metrics=run_cfg["metrics"],
                    artifacts=run_cfg["artifacts"],
                    status="completed",
                    start_time=f"2024-01-{10 + i}T{8 + i:02d}:00:00Z",
                    end_time=f"2024-01-{10 + i}T{9 + i:02d}:30:00Z",
                )
                self._runs[exp.id].append(run)
                self._all_runs[run.id] = run

    # ── Experiment operations ──

    def create_experiment(self, name: str, description: str) -> Experiment:
        """Create a new experiment."""
        exp_id = f"exp-{uuid.uuid4().hex[:8]}"
        exp = Experiment(
            id=exp_id,
            name=name,
            description=description,
            created_at="2024-01-15T10:00:00Z",
        )
        self._experiments[exp_id] = exp
        self._runs[exp_id] = []
        return exp

    def list_experiments(self) -> list[Experiment]:
        """Return all experiments."""
        return list(self._experiments.values())

    def get_experiment(self, exp_id: str) -> Optional[Experiment]:
        """Return a single experiment by ID."""
        return self._experiments.get(exp_id)

    # ── Run operations ──

    def create_run(
        self,
        experiment_id: str,
        run_name: str,
        params: dict,
        metrics: dict,
        artifacts: list[str],
        status: str,
    ) -> Optional[ExperimentRun]:
        """Log a new run in an experiment. Returns None if experiment not found."""
        if experiment_id not in self._experiments:
            return None
        run_id = f"run-{uuid.uuid4().hex[:8]}"
        run = ExperimentRun(
            id=run_id,
            experiment_id=experiment_id,
            run_name=run_name,
            params=params,
            metrics=metrics,
            artifacts=artifacts,
            status=status,
            start_time="2024-01-15T10:00:00Z",
            end_time="2024-01-15T10:30:00Z",
        )
        self._runs[experiment_id].append(run)
        self._all_runs[run.id] = run
        return run

    def list_runs(self, experiment_id: str) -> Optional[list[ExperimentRun]]:
        """Return all runs for an experiment."""
        if experiment_id not in self._experiments:
            return None
        return self._runs.get(experiment_id, [])

    def get_run(self, run_id: str) -> Optional[ExperimentRun]:
        """Return a single run by ID."""
        return self._all_runs.get(run_id)

    def compare_metrics(self, experiment_id: str) -> Optional[list[MetricComparison]]:
        """Compare metrics across all runs in an experiment."""
        if experiment_id not in self._experiments:
            return None
        runs = self._runs.get(experiment_id, [])
        if not runs:
            return []

        # Gather all metric names across runs
        all_metrics: set[str] = set()
        for run in runs:
            all_metrics.update(run.metrics.keys())

        comparisons = []
        for metric_name in sorted(all_metrics):
            run_entries = []
            for run in runs:
                if metric_name in run.metrics:
                    run_entries.append({
                        "run_id": run.id,
                        "run_name": run.run_name,
                        "value": run.metrics[metric_name],
                    })
            comparisons.append(MetricComparison(
                metric_name=metric_name,
                runs=run_entries,
            ))

        return comparisons


# Singleton repository instance
repo = ExperimentRepository(seed=True)
