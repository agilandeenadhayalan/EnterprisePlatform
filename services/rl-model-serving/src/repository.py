"""
In-memory RL model serving repository with pre-seeded data.
"""

import random
import time
import uuid
from datetime import datetime, timezone

from models import RLModel, ModelPrediction, ModelComparison


class ModelServingRepository:
    """In-memory store for RL models, predictions, and comparisons."""

    def __init__(self, seed: bool = False):
        self.models: dict[str, RLModel] = {}
        self.predictions: list[ModelPrediction] = []
        self.comparisons: list[ModelComparison] = []
        if seed:
            self._seed()

    def _seed(self):
        now = datetime.now(timezone.utc).isoformat()

        models = [
            RLModel("model-001", "Q-Learning Dispatch", "v1", "q_learning", "active",
                    {"avg_reward": 0.72, "episodes": 5000, "convergence": 0.95}, now, now),
            RLModel("model-002", "Q-Learning Dispatch", "v2", "q_learning", "active",
                    {"avg_reward": 0.81, "episodes": 10000, "convergence": 0.98}, now, now),
            RLModel("model-003", "DQN Dispatch", "v1", "dqn", "staging",
                    {"avg_reward": 0.78, "episodes": 8000, "convergence": 0.96}, now, now),
            RLModel("model-004", "SARSA Navigator", "v1", "sarsa", "retired",
                    {"avg_reward": 0.65, "episodes": 3000, "convergence": 0.88}, now, now),
        ]
        for m in models:
            self.models[m.id] = m

        predictions = [
            ModelPrediction("pred-001", "model-001", {"driver_pos": [3, 4], "request_pos": [5, 6]}, "move_right", 0.85, 12.5, now),
            ModelPrediction("pred-002", "model-001", {"driver_pos": [1, 1], "request_pos": [1, 5]}, "move_up", 0.92, 11.2, now),
            ModelPrediction("pred-003", "model-002", {"driver_pos": [7, 2], "request_pos": [5, 2]}, "move_left", 0.88, 10.8, now),
            ModelPrediction("pred-004", "model-002", {"driver_pos": [4, 4], "request_pos": [4, 4]}, "pickup", 0.99, 8.5, now),
            ModelPrediction("pred-005", "model-003", {"driver_pos": [0, 0], "request_pos": [9, 9]}, "move_right", 0.72, 15.3, now),
            ModelPrediction("pred-006", "model-003", {"driver_pos": [5, 5], "request_pos": [3, 3]}, "move_left", 0.80, 14.1, now),
        ]
        self.predictions.extend(predictions)

        comparisons = [
            ModelComparison("model-001", "model-002", "avg_reward", 0.72, 0.81, "model-002"),
            ModelComparison("model-002", "model-003", "avg_reward", 0.81, 0.78, "model-002"),
        ]
        self.comparisons.extend(comparisons)

    # ── Models ──

    def list_models(self, status: str | None = None, algorithm: str | None = None) -> list[RLModel]:
        models = list(self.models.values())
        if status:
            models = [m for m in models if m.status == status]
        if algorithm:
            models = [m for m in models if m.algorithm == algorithm]
        return models

    def get_model(self, model_id: str) -> RLModel | None:
        return self.models.get(model_id)

    def register_model(self, data: dict) -> RLModel:
        mid = f"model-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()
        model = RLModel(
            id=mid,
            name=data["name"],
            version=data["version"],
            algorithm=data["algorithm"],
            status="staging",
            metrics=data.get("metrics", {}),
            created_at=now,
            updated_at=now,
        )
        self.models[model.id] = model
        return model

    def promote_model(self, model_id: str) -> RLModel | None:
        model = self.models.get(model_id)
        if not model:
            return None
        model.status = "active"
        model.updated_at = datetime.now(timezone.utc).isoformat()
        return model

    def retire_model(self, model_id: str) -> RLModel | None:
        model = self.models.get(model_id)
        if not model:
            return None
        model.status = "retired"
        model.updated_at = datetime.now(timezone.utc).isoformat()
        return model

    # ── Predictions ──

    def predict(self, model_id: str, state_input: dict) -> ModelPrediction | None:
        model = self.models.get(model_id)
        if not model:
            return None

        # Simulate prediction based on algorithm
        actions = ["move_up", "move_down", "move_left", "move_right", "pickup", "wait"]
        action = random.choice(actions)
        confidence = round(random.uniform(0.6, 0.99), 2)
        latency = round(random.uniform(5.0, 20.0), 1)

        now = datetime.now(timezone.utc).isoformat()
        pred = ModelPrediction(
            id=f"pred-{uuid.uuid4().hex[:8]}",
            model_id=model_id,
            state_input=state_input,
            action_output=action,
            confidence=confidence,
            latency_ms=latency,
            created_at=now,
        )
        self.predictions.append(pred)
        return pred

    # ── Compare ──

    def compare_models(self, model_a_id: str, model_b_id: str, metric: str) -> ModelComparison | None:
        model_a = self.models.get(model_a_id)
        model_b = self.models.get(model_b_id)
        if not model_a or not model_b:
            return None
        val_a = model_a.metrics.get(metric, 0.0)
        val_b = model_b.metrics.get(metric, 0.0)
        winner = model_a_id if val_a >= val_b else model_b_id
        comparison = ModelComparison(model_a_id, model_b_id, metric, val_a, val_b, winner)
        self.comparisons.append(comparison)
        return comparison

    # ── Stats ──

    def get_stats(self) -> dict:
        by_status: dict[str, int] = {}
        by_algorithm: dict[str, int] = {}
        for m in self.models.values():
            by_status[m.status] = by_status.get(m.status, 0) + 1
            by_algorithm[m.algorithm] = by_algorithm.get(m.algorithm, 0) + 1
        return {
            "total_models": len(self.models),
            "by_status": by_status,
            "by_algorithm": by_algorithm,
            "total_predictions": len(self.predictions),
        }


REPO_CLASS = ModelServingRepository
repo = ModelServingRepository(seed=True)
