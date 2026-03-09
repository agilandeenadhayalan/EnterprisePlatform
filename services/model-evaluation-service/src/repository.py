"""
Model evaluation repository — in-memory evaluation store.

Pre-seeds with 5 evaluation results for different models/versions
with realistic regression metrics (RMSE, MAE, R-squared, MAPE).
"""

import random
import uuid
from typing import Optional

from models import EvaluationResult, ModelComparison


class EvaluationRepository:
    """In-memory evaluation result store."""

    def __init__(self, seed: bool = True):
        self._results: dict[str, EvaluationResult] = {}
        self._rng = random.Random(42)
        if seed:
            self._seed()

    def _seed(self):
        """Pre-seed with 5 evaluation results."""
        evals = [
            EvaluationResult(
                id="eval-001",
                model_name="fare_predictor",
                model_version="2.0.0",
                dataset_id="ds-rides-2024q1",
                task_type="regression",
                metrics={"rmse": 3.42, "mae": 2.18, "r2": 0.891, "mape": 8.7},
                evaluated_at="2024-01-10T14:00:00+00:00",
            ),
            EvaluationResult(
                id="eval-002",
                model_name="fare_predictor",
                model_version="2.1.0",
                dataset_id="ds-rides-2024q1",
                task_type="regression",
                metrics={"rmse": 2.95, "mae": 1.87, "r2": 0.923, "mape": 7.2},
                evaluated_at="2024-01-12T10:00:00+00:00",
            ),
            EvaluationResult(
                id="eval-003",
                model_name="demand_predictor",
                model_version="1.3.0",
                dataset_id="ds-zones-2024q1",
                task_type="regression",
                metrics={"rmse": 5.67, "mae": 4.12, "r2": 0.845, "mape": 12.3},
                evaluated_at="2024-01-13T09:00:00+00:00",
            ),
            EvaluationResult(
                id="eval-004",
                model_name="eta_predictor",
                model_version="3.0.1",
                dataset_id="ds-routes-2024q1",
                task_type="regression",
                metrics={"rmse": 1.89, "mae": 1.34, "r2": 0.952, "mape": 5.1},
                evaluated_at="2024-01-14T11:00:00+00:00",
            ),
            EvaluationResult(
                id="eval-005",
                model_name="demand_predictor",
                model_version="1.2.0",
                dataset_id="ds-zones-2024q1",
                task_type="regression",
                metrics={"rmse": 6.21, "mae": 4.58, "r2": 0.812, "mape": 14.1},
                evaluated_at="2024-01-09T16:00:00+00:00",
            ),
        ]
        for ev in evals:
            self._results[ev.id] = ev

    def run_evaluation(
        self, model_name: str, model_version: str, dataset_id: str
    ) -> EvaluationResult:
        """Run an evaluation (simulated) and store the result."""
        eval_id = f"eval-{uuid.uuid4().hex[:8]}"
        # Generate realistic metrics
        rmse = round(self._rng.uniform(1.5, 8.0), 2)
        mae = round(rmse * self._rng.uniform(0.55, 0.75), 2)
        r2 = round(max(0.0, 1.0 - (rmse / 15.0) ** 2), 3)
        mape = round(rmse * self._rng.uniform(1.5, 3.0), 1)

        result = EvaluationResult(
            id=eval_id,
            model_name=model_name,
            model_version=model_version,
            dataset_id=dataset_id,
            task_type="regression",
            metrics={"rmse": rmse, "mae": mae, "r2": r2, "mape": mape},
        )
        self._results[eval_id] = result
        return result

    def list_results(self) -> list[EvaluationResult]:
        """List all evaluation results, newest first."""
        return sorted(
            self._results.values(),
            key=lambda r: r.evaluated_at,
            reverse=True,
        )

    def get_result(self, eval_id: str) -> Optional[EvaluationResult]:
        """Get a specific evaluation result."""
        return self._results.get(eval_id)

    def compare_models(
        self, model_a: str, model_b: str, dataset_id: str
    ) -> Optional[ModelComparison]:
        """Compare two models on the same dataset using their latest evals."""
        evals_a = [
            r for r in self._results.values()
            if r.model_name == model_a and r.dataset_id == dataset_id
        ]
        evals_b = [
            r for r in self._results.values()
            if r.model_name == model_b and r.dataset_id == dataset_id
        ]
        if not evals_a or not evals_b:
            return None

        best_a = min(evals_a, key=lambda r: r.metrics.get("rmse", float("inf")))
        best_b = min(evals_b, key=lambda r: r.metrics.get("rmse", float("inf")))

        rmse_a = best_a.metrics.get("rmse", float("inf"))
        rmse_b = best_b.metrics.get("rmse", float("inf"))

        if rmse_a <= rmse_b:
            winner = model_a
            improvement_pct = round(((rmse_b - rmse_a) / rmse_b) * 100, 2) if rmse_b > 0 else 0.0
        else:
            winner = model_b
            improvement_pct = round(((rmse_a - rmse_b) / rmse_a) * 100, 2) if rmse_a > 0 else 0.0

        return ModelComparison(
            model_a=model_a,
            model_b=model_b,
            dataset_id=dataset_id,
            metrics_a=best_a.metrics,
            metrics_b=best_b.metrics,
            winner=winner,
            improvement_pct=improvement_pct,
        )

    def get_leaderboard(
        self, metric: str = "rmse", task: str = "regression"
    ) -> list[dict]:
        """Get model leaderboard ranked by the specified metric."""
        # Filter by task type
        filtered = [r for r in self._results.values() if r.task_type == task]

        # For each model, get the best evaluation by the metric
        best_by_model: dict[str, EvaluationResult] = {}
        for r in filtered:
            key = r.model_name
            if key not in best_by_model:
                best_by_model[key] = r
            else:
                current_val = best_by_model[key].metrics.get(metric, float("inf"))
                new_val = r.metrics.get(metric, float("inf"))
                # For rmse, mae, mape: lower is better. For r2: higher is better.
                if metric == "r2":
                    if new_val > current_val:
                        best_by_model[key] = r
                else:
                    if new_val < current_val:
                        best_by_model[key] = r

        # Sort: r2 descending, others ascending
        entries = list(best_by_model.values())
        if metric == "r2":
            entries.sort(key=lambda r: r.metrics.get(metric, 0), reverse=True)
        else:
            entries.sort(key=lambda r: r.metrics.get(metric, float("inf")))

        result = []
        for rank, entry in enumerate(entries, 1):
            result.append({
                "rank": rank,
                "model_name": entry.model_name,
                "model_version": entry.model_version,
                "metric_value": entry.metrics.get(metric, 0),
                "dataset_id": entry.dataset_id,
                "evaluated_at": entry.evaluated_at,
            })
        return result


repo = EvaluationRepository(seed=True)
