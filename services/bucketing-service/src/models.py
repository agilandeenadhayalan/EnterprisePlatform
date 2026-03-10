"""
Domain models for the Bucketing service.
"""


class BucketAssignment:
    """A user's bucket assignment for an experiment."""

    def __init__(
        self,
        id: str,
        experiment_id: str,
        user_id: str,
        variant: str,
        bucket_hash: str,
        assigned_at: str = "2026-03-01T00:00:00Z",
    ):
        self.id = id
        self.experiment_id = experiment_id
        self.user_id = user_id
        self.variant = variant
        self.bucket_hash = bucket_hash
        self.assigned_at = assigned_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "experiment_id": self.experiment_id,
            "user_id": self.user_id,
            "variant": self.variant,
            "bucket_hash": self.bucket_hash,
            "assigned_at": self.assigned_at,
        }


class TrafficAllocation:
    """Traffic allocation for an experiment."""

    def __init__(self, experiment_id: str, variant_weights: dict, total_allocated: int):
        self.experiment_id = experiment_id
        self.variant_weights = variant_weights
        self.total_allocated = total_allocated

    def to_dict(self) -> dict:
        return {
            "experiment_id": self.experiment_id,
            "variant_weights": self.variant_weights,
            "total_allocated": self.total_allocated,
        }


class BucketConfig:
    """Configuration for the bucketing hash."""

    def __init__(self, hash_seed: str, hash_algorithm: str):
        self.hash_seed = hash_seed
        self.hash_algorithm = hash_algorithm

    def to_dict(self) -> dict:
        return {
            "hash_seed": self.hash_seed,
            "hash_algorithm": self.hash_algorithm,
        }
