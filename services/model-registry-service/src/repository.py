"""
Model registry repository — in-memory model registry.

Pre-seeds with 3 registered models:
- fare_predictor: 3 versions (v1 archived, v2 staging, v3 production)
- demand_predictor: 2 versions (v1 archived, v2 production)
- eta_predictor: 1 version (v1 production)
"""

from datetime import datetime, timezone
from typing import Optional

from models import RegisteredModel, ModelVersion, StageTransition


class ModelRegistryRepository:
    """In-memory model registry store."""

    def __init__(self, seed: bool = True):
        self._models: dict[str, RegisteredModel] = {}
        if seed:
            self._seed()

    def _seed(self):
        """Pre-seed with 3 registered models."""
        # fare_predictor — 3 versions
        fare = RegisteredModel(
            name="fare_predictor",
            description="Predicts ride fare based on distance, duration, and surge",
            model_type="xgboost",
            task_type="regression",
            created_at="2024-01-01T10:00:00+00:00",
        )
        fare.versions = [
            ModelVersion(
                version=1, model_name="fare_predictor", stage="archived",
                run_id="run-fare-001",
                metrics={"rmse": 4.12, "mae": 2.85, "r2": 0.841},
                hyperparameters={"n_estimators": 100, "max_depth": 6, "learning_rate": 0.1},
                created_at="2024-01-01T10:00:00+00:00",
                transitioned_at="2024-01-08T10:00:00+00:00",
            ),
            ModelVersion(
                version=2, model_name="fare_predictor", stage="staging",
                run_id="run-fare-002",
                metrics={"rmse": 3.42, "mae": 2.18, "r2": 0.891},
                hyperparameters={"n_estimators": 200, "max_depth": 8, "learning_rate": 0.05},
                created_at="2024-01-05T10:00:00+00:00",
                transitioned_at="2024-01-10T10:00:00+00:00",
            ),
            ModelVersion(
                version=3, model_name="fare_predictor", stage="production",
                run_id="run-fare-003",
                metrics={"rmse": 2.95, "mae": 1.87, "r2": 0.923},
                hyperparameters={"n_estimators": 300, "max_depth": 10, "learning_rate": 0.03},
                created_at="2024-01-10T10:00:00+00:00",
                transitioned_at="2024-01-12T10:00:00+00:00",
            ),
        ]
        self._models["fare_predictor"] = fare

        # demand_predictor — 2 versions
        demand = RegisteredModel(
            name="demand_predictor",
            description="Predicts ride demand per zone per hour",
            model_type="sklearn",
            task_type="regression",
            created_at="2024-01-02T10:00:00+00:00",
        )
        demand.versions = [
            ModelVersion(
                version=1, model_name="demand_predictor", stage="archived",
                run_id="run-demand-001",
                metrics={"rmse": 6.21, "mae": 4.58, "r2": 0.812},
                hyperparameters={"n_estimators": 50, "max_depth": 5},
                created_at="2024-01-02T10:00:00+00:00",
                transitioned_at="2024-01-09T10:00:00+00:00",
            ),
            ModelVersion(
                version=2, model_name="demand_predictor", stage="production",
                run_id="run-demand-002",
                metrics={"rmse": 5.67, "mae": 4.12, "r2": 0.845},
                hyperparameters={"n_estimators": 150, "max_depth": 7},
                created_at="2024-01-07T10:00:00+00:00",
                transitioned_at="2024-01-11T10:00:00+00:00",
            ),
        ]
        self._models["demand_predictor"] = demand

        # eta_predictor — 1 version
        eta = RegisteredModel(
            name="eta_predictor",
            description="Predicts estimated time of arrival for rides",
            model_type="lightgbm",
            task_type="regression",
            created_at="2024-01-03T10:00:00+00:00",
        )
        eta.versions = [
            ModelVersion(
                version=1, model_name="eta_predictor", stage="production",
                run_id="run-eta-001",
                metrics={"rmse": 1.89, "mae": 1.34, "r2": 0.952},
                hyperparameters={"n_estimators": 200, "num_leaves": 31, "learning_rate": 0.05},
                created_at="2024-01-03T10:00:00+00:00",
                transitioned_at="2024-01-05T10:00:00+00:00",
            ),
        ]
        self._models["eta_predictor"] = eta

    def register_model(
        self, name: str, description: str = "", model_type: str = "sklearn", task_type: str = "regression"
    ) -> RegisteredModel:
        """Register a new model."""
        if name in self._models:
            raise ValueError(f"Model '{name}' is already registered")
        model = RegisteredModel(
            name=name,
            description=description,
            model_type=model_type,
            task_type=task_type,
        )
        self._models[name] = model
        return model

    def list_models(self) -> list[RegisteredModel]:
        """List all registered models."""
        return sorted(self._models.values(), key=lambda m: m.created_at)

    def get_model(self, name: str) -> Optional[RegisteredModel]:
        """Get a registered model by name."""
        return self._models.get(name)

    def list_versions(self, model_name: str) -> list[ModelVersion]:
        """List all versions of a model."""
        model = self._models.get(model_name)
        if model is None:
            return []
        return sorted(model.versions, key=lambda v: v.version, reverse=True)

    def create_version(
        self,
        model_name: str,
        run_id: Optional[str] = None,
        metrics: Optional[dict] = None,
        hyperparameters: Optional[dict] = None,
    ) -> Optional[ModelVersion]:
        """Create a new version for a model."""
        model = self._models.get(model_name)
        if model is None:
            return None
        next_version = (model.latest_version or 0) + 1
        version = ModelVersion(
            version=next_version,
            model_name=model_name,
            stage="none",
            run_id=run_id,
            metrics=metrics or {},
            hyperparameters=hyperparameters or {},
        )
        model.versions.append(version)
        return version

    def transition_stage(
        self, model_name: str, version_num: int, stage: str, reason: str = ""
    ) -> Optional[tuple[StageTransition, ModelVersion]]:
        """Transition a model version to a new stage."""
        model = self._models.get(model_name)
        if model is None:
            return None

        target_version = None
        for v in model.versions:
            if v.version == version_num:
                target_version = v
                break

        if target_version is None:
            return None

        # If transitioning to production, demote current production version
        if stage == "production":
            for v in model.versions:
                if v.stage == "production" and v.version != version_num:
                    v.stage = "archived"
                    v.transitioned_at = datetime.now(timezone.utc).isoformat()

        from_stage = target_version.stage
        target_version.stage = stage
        target_version.transitioned_at = datetime.now(timezone.utc).isoformat()

        transition = StageTransition(
            from_stage=from_stage,
            to_stage=stage,
            reason=reason,
        )
        return transition, target_version

    def get_production_version(self, model_name: str) -> Optional[ModelVersion]:
        """Get the production version of a model."""
        model = self._models.get(model_name)
        if model is None:
            return None
        for v in model.versions:
            if v.stage == "production":
                return v
        return None


repo = ModelRegistryRepository(seed=True)
