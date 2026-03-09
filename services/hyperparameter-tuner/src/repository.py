"""
Hyperparameter Tuner repository — in-memory pre-seeded search data.

Seeds completed grid and random searches with trials, each containing
parameter configurations and resulting metrics.
"""

import random
import uuid
from typing import Optional

from models import HyperparameterSearch, SearchTrial, ParamSpace


class TunerRepository:
    """In-memory tuner data store with pre-seeded sample data."""

    def __init__(self, seed: bool = True):
        self._searches: dict[str, HyperparameterSearch] = {}
        self._trials: dict[str, list[SearchTrial]] = {}
        self._rng = random.Random(42)

        if seed:
            self._seed_data()

    def _seed_data(self):
        """Pre-populate with completed hyperparameter searches and trials."""

        # ── Search 1: Grid search for fare predictor (6 trials) ──
        search1_id = "search-001"
        search1_space = [
            ParamSpace(param_name="n_estimators", type="int", min=50, max=300),
            ParamSpace(param_name="max_depth", type="int", min=5, max=20),
            ParamSpace(param_name="min_samples_split", type="int", min=2, max=10),
        ]

        grid_configs = [
            {"n_estimators": 50, "max_depth": 5, "min_samples_split": 2},
            {"n_estimators": 100, "max_depth": 10, "min_samples_split": 2},
            {"n_estimators": 150, "max_depth": 10, "min_samples_split": 5},
            {"n_estimators": 200, "max_depth": 15, "min_samples_split": 5},
            {"n_estimators": 250, "max_depth": 15, "min_samples_split": 10},
            {"n_estimators": 300, "max_depth": 20, "min_samples_split": 10},
        ]

        trials1 = []
        best_val_loss_1 = float("inf")
        best_trial_1 = None
        for i, params in enumerate(grid_configs):
            trial_id = f"trial-1-{i + 1:02d}"
            val_loss = round(3.0 + self._rng.uniform(-0.8, 1.5) - (params["n_estimators"] / 500), 4)
            train_loss = round(val_loss - self._rng.uniform(0.1, 0.5), 4)
            trial = SearchTrial(
                id=trial_id,
                search_id=search1_id,
                params=params,
                metrics={
                    "val_loss": val_loss,
                    "train_loss": train_loss,
                    "val_rmse": round(val_loss * 1.1, 4),
                    "train_rmse": round(train_loss * 1.1, 4),
                },
                status="completed",
                duration_seconds=round(self._rng.uniform(30.0, 120.0), 1),
            )
            trials1.append(trial)
            if val_loss < best_val_loss_1:
                best_val_loss_1 = val_loss
                best_trial_1 = trial_id

        self._trials[search1_id] = trials1
        self._searches[search1_id] = HyperparameterSearch(
            id=search1_id,
            model_type="fare_predictor_rf",
            search_strategy="grid",
            param_space=search1_space,
            objective_metric="val_loss",
            status="completed",
            best_trial_id=best_trial_1,
            created_at="2024-01-10T08:00:00Z",
        )

        # ── Search 2: Random search for neural network (10 trials) ──
        search2_id = "search-002"
        search2_space = [
            ParamSpace(param_name="learning_rate", type="float", min=0.0001, max=0.01),
            ParamSpace(param_name="batch_size", type="categorical", choices=[64, 128, 256, 512]),
            ParamSpace(param_name="dropout", type="float", min=0.0, max=0.5),
        ]

        trials2 = []
        best_val_loss_2 = float("inf")
        best_trial_2 = None
        for i in range(10):
            trial_id = f"trial-2-{i + 1:02d}"
            lr = round(self._rng.uniform(0.0001, 0.01), 5)
            bs = self._rng.choice([64, 128, 256, 512])
            dropout = round(self._rng.uniform(0.0, 0.5), 2)
            params = {
                "learning_rate": lr,
                "batch_size": bs,
                "dropout": dropout,
            }
            # Lower lr with moderate dropout tends to be better
            val_loss = round(2.0 + lr * 100 + abs(dropout - 0.2) * 2 + self._rng.uniform(-0.3, 0.3), 4)
            train_loss = round(val_loss - self._rng.uniform(0.1, 0.4), 4)
            trial = SearchTrial(
                id=trial_id,
                search_id=search2_id,
                params=params,
                metrics={
                    "val_loss": val_loss,
                    "train_loss": train_loss,
                    "val_mae": round(val_loss * 0.8, 4),
                    "train_mae": round(train_loss * 0.8, 4),
                },
                status="completed",
                duration_seconds=round(self._rng.uniform(60.0, 300.0), 1),
            )
            trials2.append(trial)
            if val_loss < best_val_loss_2:
                best_val_loss_2 = val_loss
                best_trial_2 = trial_id

        self._trials[search2_id] = trials2
        self._searches[search2_id] = HyperparameterSearch(
            id=search2_id,
            model_type="fare_predictor_nn",
            search_strategy="random",
            param_space=search2_space,
            objective_metric="val_loss",
            status="completed",
            best_trial_id=best_trial_2,
            created_at="2024-01-12T14:00:00Z",
        )

    # ── Search operations ──

    def create_search(
        self,
        model_type: str,
        search_strategy: str,
        param_space: list[ParamSpace],
        objective_metric: str,
    ) -> HyperparameterSearch:
        """Create a new hyperparameter search."""
        search_id = f"search-{uuid.uuid4().hex[:8]}"
        search = HyperparameterSearch(
            id=search_id,
            model_type=model_type,
            search_strategy=search_strategy,
            param_space=param_space,
            objective_metric=objective_metric,
            status="pending",
            created_at="2024-01-15T10:00:00Z",
        )
        self._searches[search_id] = search
        self._trials[search_id] = []
        return search

    def list_searches(self, status: Optional[str] = None) -> list[HyperparameterSearch]:
        """List all searches, optionally filtered by status."""
        searches = list(self._searches.values())
        if status:
            searches = [s for s in searches if s.status == status]
        return searches

    def get_search(self, search_id: str) -> Optional[HyperparameterSearch]:
        """Return a single search by ID."""
        return self._searches.get(search_id)

    def get_trials(self, search_id: str) -> Optional[list[SearchTrial]]:
        """Return all trials for a search."""
        return self._trials.get(search_id)

    def get_best_trial(self, search_id: str) -> Optional[SearchTrial]:
        """Return the best trial for a search."""
        search = self._searches.get(search_id)
        if search is None or search.best_trial_id is None:
            return None
        trials = self._trials.get(search_id, [])
        for trial in trials:
            if trial.id == search.best_trial_id:
                return trial
        return None


# Singleton repository instance
repo = TunerRepository(seed=True)
