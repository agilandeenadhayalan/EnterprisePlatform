"""
Feature Types for ML Systems
=============================

In production ML systems, features (the input variables to a model) come from
different sources and have different characteristics:

**Online Features** are served in real-time from low-latency stores like Redis.
They are computed from recent events (e.g., "driver's average rating in the last
hour") and must be fresh -- stale features degrade prediction quality.

**Offline Features** are computed in batch from historical data stores like
ClickHouse or BigQuery. They provide richer, more complete views (e.g., "driver's
total lifetime trips") but can tolerate hours of staleness.

**Feature Groups** organize related features for a single entity type. For example,
a "driver_profile" group might contain experience_level, avg_rating, and
preferred_zones -- all keyed by driver_id.

This separation matters because:
1. Training uses offline features (completeness over freshness)
2. Inference uses online features (freshness over completeness)
3. Feature groups help manage the hundreds of features in production systems
"""

from __future__ import annotations


class Entity:
    """Represents an entity that features are computed for.

    In a ride-sharing platform, common entities include:
    - driver (entity_id = driver's UUID)
    - rider (entity_id = rider's UUID)
    - zone (entity_id = zone code like 'manhattan_midtown')

    Every feature is associated with exactly one entity type.
    """

    def __init__(self, entity_type: str, entity_id: str) -> None:
        if not entity_type:
            raise ValueError("entity_type cannot be empty")
        if not entity_id:
            raise ValueError("entity_id cannot be empty")
        self.entity_type = entity_type
        self.entity_id = entity_id

    def __repr__(self) -> str:
        return f"Entity(type={self.entity_type!r}, id={self.entity_id!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            return NotImplemented
        return self.entity_type == other.entity_type and self.entity_id == other.entity_id

    def __hash__(self) -> int:
        return hash((self.entity_type, self.entity_id))


class OnlineFeature:
    """A feature served in real-time from a low-latency store (e.g., Redis).

    Online features are used during model inference when prediction latency
    matters. They are typically derived from recent events and must meet a
    freshness SLA -- if the feature is too stale, the prediction quality
    degrades.

    Attributes:
        name: Human-readable feature name (e.g., 'driver_avg_speed_1h').
        entity_type: The entity this feature belongs to (e.g., 'driver').
        value_type: Data type of the feature value ('float', 'int', 'string').
        description: Documentation for what this feature represents.
        freshness_sla_seconds: Maximum allowed staleness in seconds.
    """

    def __init__(
        self,
        name: str,
        entity_type: str,
        value_type: str,
        description: str,
        freshness_sla_seconds: float,
    ) -> None:
        if not name:
            raise ValueError("name cannot be empty")
        if value_type not in ("float", "int", "string"):
            raise ValueError(f"value_type must be float, int, or string; got {value_type!r}")
        if freshness_sla_seconds <= 0:
            raise ValueError("freshness_sla_seconds must be positive")

        self.name = name
        self.entity_type = entity_type
        self.value_type = value_type
        self.description = description
        self.freshness_sla_seconds = freshness_sla_seconds

    def is_fresh(self, last_updated_at: float, current_time: float) -> bool:
        """Check whether this feature meets its freshness SLA.

        Args:
            last_updated_at: Unix timestamp when the feature was last computed.
            current_time: Current unix timestamp.

        Returns:
            True if the feature is within its freshness SLA.
        """
        age_seconds = current_time - last_updated_at
        return age_seconds <= self.freshness_sla_seconds

    def __repr__(self) -> str:
        return (
            f"OnlineFeature(name={self.name!r}, entity={self.entity_type!r}, "
            f"sla={self.freshness_sla_seconds}s)"
        )


class OfflineFeature:
    """A feature computed in batch from historical data (e.g., ClickHouse).

    Offline features are used during model training when we need complete
    historical data. They are typically computed by scheduled batch jobs
    (e.g., every hour or daily) and stored in analytical databases.

    The computation_query describes HOW to compute this feature -- in a real
    system this would be a SQL query or a transformation definition.

    Attributes:
        name: Human-readable feature name (e.g., 'driver_lifetime_trips').
        entity_type: The entity this feature belongs to (e.g., 'driver').
        value_type: Data type ('float', 'int', 'string').
        description: Documentation for what this feature represents.
        computation_query: Description or SQL of how to compute the feature.
    """

    def __init__(
        self,
        name: str,
        entity_type: str,
        value_type: str,
        description: str,
        computation_query: str,
    ) -> None:
        if not name:
            raise ValueError("name cannot be empty")
        if value_type not in ("float", "int", "string"):
            raise ValueError(f"value_type must be float, int, or string; got {value_type!r}")

        self.name = name
        self.entity_type = entity_type
        self.value_type = value_type
        self.description = description
        self.computation_query = computation_query

    def __repr__(self) -> str:
        return (
            f"OfflineFeature(name={self.name!r}, entity={self.entity_type!r})"
        )


class FeatureGroup:
    """A logical group of related features for a single entity type.

    Feature groups help organize the many features in a production ML system.
    For example, a 'driver_behavior' group might contain:
    - avg_speed_1h (OnlineFeature)
    - hard_brake_count_1h (OnlineFeature)
    - lifetime_trips (OfflineFeature)

    All features in a group must share the same entity_type.

    Validation rules:
    - No duplicate feature names within a group.
    - All features must have the same entity_type as the group.
    """

    def __init__(self, name: str, entity_type: str) -> None:
        if not name:
            raise ValueError("name cannot be empty")
        if not entity_type:
            raise ValueError("entity_type cannot be empty")

        self.name = name
        self.entity_type = entity_type
        self._features: dict[str, OnlineFeature | OfflineFeature] = {}

    def add_feature(self, feature: OnlineFeature | OfflineFeature) -> None:
        """Add a feature to this group.

        Raises:
            ValueError: If a feature with the same name already exists,
                        or the feature's entity_type doesn't match the group.
        """
        if feature.name in self._features:
            raise ValueError(
                f"Duplicate feature name {feature.name!r} in group {self.name!r}"
            )
        if feature.entity_type != self.entity_type:
            raise ValueError(
                f"Feature entity_type {feature.entity_type!r} does not match "
                f"group entity_type {self.entity_type!r}"
            )
        self._features[feature.name] = feature

    def get_feature(self, name: str) -> OnlineFeature | OfflineFeature:
        """Retrieve a feature by name.

        Raises:
            KeyError: If no feature with that name exists in this group.
        """
        if name not in self._features:
            raise KeyError(f"Feature {name!r} not found in group {self.name!r}")
        return self._features[name]

    def list_features(self) -> list[str]:
        """Return a sorted list of feature names in this group."""
        return sorted(self._features.keys())

    def validate(self) -> list[str]:
        """Validate the feature group configuration.

        Returns:
            A list of validation error messages (empty if valid).
        """
        errors: list[str] = []

        # Check entity type consistency
        for feat_name, feat in self._features.items():
            if feat.entity_type != self.entity_type:
                errors.append(
                    f"Feature {feat_name!r} has entity_type {feat.entity_type!r} "
                    f"but group expects {self.entity_type!r}"
                )

        return errors

    def __len__(self) -> int:
        return len(self._features)

    def __repr__(self) -> str:
        return (
            f"FeatureGroup(name={self.name!r}, entity={self.entity_type!r}, "
            f"features={len(self._features)})"
        )
