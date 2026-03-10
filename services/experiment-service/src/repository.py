"""
In-memory experiment repository with pre-seeded data.
"""

import uuid
from datetime import datetime, timezone

from models import Experiment


class ExperimentRepository:
    """In-memory store for experiments."""

    def __init__(self, seed: bool = False):
        self.experiments: dict[str, Experiment] = {}
        if seed:
            self._seed()

    def _seed(self):
        now = datetime.now(timezone.utc).isoformat()

        experiments = [
            Experiment(
                "exp-001", "Checkout Button Color", "A/B test for checkout button color",
                "ab_test", "running",
                [{"name": "control", "weight": 0.5, "config": {"color": "blue"}},
                 {"name": "variant_a", "weight": 0.5, "config": {"color": "green"}}],
                [{"attribute": "country", "operator": "eq", "value": "US"}],
                100.0, now, now,
            ),
            Experiment(
                "exp-002", "Pricing Page Layout", "A/B test for pricing page",
                "ab_test", "completed",
                [{"name": "control", "weight": 0.5, "config": {"layout": "grid"}},
                 {"name": "variant_a", "weight": 0.5, "config": {"layout": "list"}}],
                [{"attribute": "platform", "operator": "eq", "value": "web"}],
                100.0, now, now,
            ),
            Experiment(
                "exp-003", "Dark Mode Toggle", "Feature flag for dark mode",
                "feature_flag", "running",
                [{"name": "off", "weight": 0.7, "config": {"enabled": False}},
                 {"name": "on", "weight": 0.3, "config": {"enabled": True}}],
                [{"attribute": "tier", "operator": "eq", "value": "premium"}],
                100.0, now, now,
            ),
            Experiment(
                "exp-004", "New Onboarding Flow", "Feature flag for onboarding",
                "feature_flag", "paused",
                [{"name": "off", "weight": 0.8, "config": {"enabled": False}},
                 {"name": "on", "weight": 0.2, "config": {"enabled": True}}],
                [],
                50.0, now, now,
            ),
            Experiment(
                "exp-005", "Recommendation Algorithm", "Multi-armed bandit for recs",
                "mab", "draft",
                [{"name": "collaborative", "weight": 0.34, "config": {"algo": "cf"}},
                 {"name": "content_based", "weight": 0.33, "config": {"algo": "cb"}},
                 {"name": "hybrid", "weight": 0.33, "config": {"algo": "hybrid"}}],
                [],
                100.0, now, now,
            ),
            Experiment(
                "exp-006", "Landing Page MVT", "Multivariate test for landing page",
                "mvt", "running",
                [{"name": "headline_a_image_a", "weight": 0.25, "config": {"headline": "A", "image": "A"}},
                 {"name": "headline_a_image_b", "weight": 0.25, "config": {"headline": "A", "image": "B"}},
                 {"name": "headline_b_image_a", "weight": 0.25, "config": {"headline": "B", "image": "A"}}],
                [{"attribute": "device", "operator": "eq", "value": "mobile"}],
                75.0, now, now,
            ),
        ]
        for e in experiments:
            self.experiments[e.id] = e

    # ── CRUD ──

    def list_experiments(self) -> list[Experiment]:
        return list(self.experiments.values())

    def get_experiment(self, experiment_id: str) -> Experiment | None:
        return self.experiments.get(experiment_id)

    def create_experiment(self, data: dict) -> Experiment:
        exp_id = f"exp-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()
        exp = Experiment(
            id=exp_id,
            name=data["name"],
            description=data.get("description", ""),
            experiment_type=data["experiment_type"],
            status="draft",
            variants=data.get("variants", []),
            targeting_rules=data.get("targeting_rules", []),
            traffic_percentage=data.get("traffic_percentage", 100.0),
            created_at=now,
            updated_at=now,
        )
        self.experiments[exp.id] = exp
        return exp

    def update_experiment(self, experiment_id: str, data: dict) -> Experiment | None:
        exp = self.experiments.get(experiment_id)
        if not exp:
            return None
        for field in ["name", "description", "variants", "targeting_rules", "traffic_percentage"]:
            if field in data and data[field] is not None:
                setattr(exp, field, data[field])
        exp.updated_at = datetime.now(timezone.utc).isoformat()
        return exp

    def start_experiment(self, experiment_id: str) -> Experiment | None:
        exp = self.experiments.get(experiment_id)
        if not exp:
            return None
        if exp.status not in ("draft", "paused"):
            return "invalid_status"
        exp.status = "running"
        exp.updated_at = datetime.now(timezone.utc).isoformat()
        return exp

    def pause_experiment(self, experiment_id: str) -> Experiment | None:
        exp = self.experiments.get(experiment_id)
        if not exp:
            return None
        if exp.status != "running":
            return "invalid_status"
        exp.status = "paused"
        exp.updated_at = datetime.now(timezone.utc).isoformat()
        return exp

    def complete_experiment(self, experiment_id: str) -> Experiment | None:
        exp = self.experiments.get(experiment_id)
        if not exp:
            return None
        if exp.status != "running":
            return "invalid_status"
        exp.status = "completed"
        exp.updated_at = datetime.now(timezone.utc).isoformat()
        return exp

    def archive_experiment(self, experiment_id: str) -> Experiment | None:
        exp = self.experiments.get(experiment_id)
        if not exp:
            return None
        exp.status = "archived"
        exp.updated_at = datetime.now(timezone.utc).isoformat()
        return exp

    # ── Stats ──

    def get_stats(self) -> dict:
        by_status: dict[str, int] = {}
        by_type: dict[str, int] = {}
        for e in self.experiments.values():
            by_status[e.status] = by_status.get(e.status, 0) + 1
            by_type[e.experiment_type] = by_type.get(e.experiment_type, 0) + 1
        return {
            "total": len(self.experiments),
            "by_status": by_status,
            "by_type": by_type,
        }


REPO_CLASS = ExperimentRepository
repo = ExperimentRepository(seed=True)
