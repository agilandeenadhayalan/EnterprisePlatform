"""
In-memory bucketing repository with pre-seeded data.
"""

import hashlib
import uuid
from datetime import datetime, timezone

from models import BucketAssignment, TrafficAllocation, BucketConfig


class BucketingRepository:
    """In-memory store for bucket assignments and traffic allocations."""

    def __init__(self, seed: bool = False):
        self.assignments: list[BucketAssignment] = []
        self.allocations: dict[str, TrafficAllocation] = {}
        self.config: BucketConfig = BucketConfig("mobility2024", "md5")
        if seed:
            self._seed()

    def _seed(self):
        now = datetime.now(timezone.utc).isoformat()

        # Traffic allocations
        allocs = [
            TrafficAllocation("exp-001", {"control": 0.5, "variant_a": 0.5}, 100),
            TrafficAllocation("exp-002", {"control": 0.5, "variant_a": 0.5}, 80),
            TrafficAllocation("exp-003", {"off": 0.7, "on": 0.3}, 50),
        ]
        for a in allocs:
            self.allocations[a.experiment_id] = a

        # Bucket assignments
        users_exp1 = ["user-001", "user-002", "user-003", "user-004", "user-005"]
        users_exp2 = ["user-001", "user-002", "user-003", "user-004"]
        users_exp3 = ["user-001", "user-002", "user-003"]

        idx = 1
        for uid in users_exp1:
            variant = self._hash_assign(
                "exp-001", uid, {"control": 0.5, "variant_a": 0.5}
            )
            h = self._compute_hash("exp-001", uid)
            self.assignments.append(
                BucketAssignment(f"ba-{idx:03d}", "exp-001", uid, variant, h, now)
            )
            idx += 1
        for uid in users_exp2:
            variant = self._hash_assign(
                "exp-002", uid, {"control": 0.5, "variant_a": 0.5}
            )
            h = self._compute_hash("exp-002", uid)
            self.assignments.append(
                BucketAssignment(f"ba-{idx:03d}", "exp-002", uid, variant, h, now)
            )
            idx += 1
        for uid in users_exp3:
            variant = self._hash_assign(
                "exp-003", uid, {"off": 0.7, "on": 0.3}
            )
            h = self._compute_hash("exp-003", uid)
            self.assignments.append(
                BucketAssignment(f"ba-{idx:03d}", "exp-003", uid, variant, h, now)
            )
            idx += 1

    def _compute_hash(self, experiment_id: str, user_id: str) -> str:
        raw = f"{self.config.hash_seed}{experiment_id}{user_id}"
        return hashlib.md5(raw.encode()).hexdigest()

    def _hash_assign(
        self, experiment_id: str, user_id: str, variant_weights: dict[str, float]
    ) -> str:
        h = self._compute_hash(experiment_id, user_id)
        hash_val = int(h, 16) % 10000
        cumulative = 0.0
        for variant, weight in variant_weights.items():
            cumulative += weight * 10000
            if hash_val < cumulative:
                return variant
        return list(variant_weights.keys())[-1]

    # ── Assignments ──

    def assign_user(self, experiment_id: str, user_id: str, variant_weights: dict[str, float]) -> BucketAssignment:
        # Check if already assigned
        for a in self.assignments:
            if a.experiment_id == experiment_id and a.user_id == user_id:
                return a
        variant = self._hash_assign(experiment_id, user_id, variant_weights)
        h = self._compute_hash(experiment_id, user_id)
        now = datetime.now(timezone.utc).isoformat()
        assignment = BucketAssignment(
            id=f"ba-{uuid.uuid4().hex[:8]}",
            experiment_id=experiment_id,
            user_id=user_id,
            variant=variant,
            bucket_hash=h,
            assigned_at=now,
        )
        self.assignments.append(assignment)
        # Update allocation count
        if experiment_id in self.allocations:
            self.allocations[experiment_id].total_allocated += 1
        return assignment

    def get_assignment(self, experiment_id: str, user_id: str) -> BucketAssignment | None:
        for a in self.assignments:
            if a.experiment_id == experiment_id and a.user_id == user_id:
                return a
        return None

    def list_assignments(self, experiment_id: str | None = None) -> list[BucketAssignment]:
        if experiment_id:
            return [a for a in self.assignments if a.experiment_id == experiment_id]
        return list(self.assignments)

    def bulk_assign(self, experiment_id: str, user_ids: list[str], variant_weights: dict[str, float]) -> list[BucketAssignment]:
        results = []
        for uid in user_ids:
            results.append(self.assign_user(experiment_id, uid, variant_weights))
        return results

    # ── Allocations ──

    def get_allocation(self, experiment_id: str) -> TrafficAllocation | None:
        return self.allocations.get(experiment_id)

    def set_allocation(self, experiment_id: str, variant_weights: dict[str, float]) -> TrafficAllocation:
        alloc = self.allocations.get(experiment_id)
        if alloc:
            alloc.variant_weights = variant_weights
        else:
            alloc = TrafficAllocation(experiment_id, variant_weights, 0)
            self.allocations[experiment_id] = alloc
        return alloc

    # ── Stats ──

    def get_stats(self) -> dict:
        by_experiment: dict[str, int] = {}
        for a in self.assignments:
            by_experiment[a.experiment_id] = by_experiment.get(a.experiment_id, 0) + 1
        return {
            "total_assignments": len(self.assignments),
            "by_experiment": by_experiment,
            "config": self.config.to_dict(),
        }


REPO_CLASS = BucketingRepository
repo = BucketingRepository(seed=True)
