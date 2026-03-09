"""
Domain models for the Feature Store service.
"""


class FeatureDefinition:
    """Metadata describing a registered feature."""

    def __init__(
        self,
        name: str,
        entity_type: str,
        value_type: str,
        source: str,
        description: str,
        freshness_sla_seconds: int,
        is_active: bool = True,
        created_at: str = "2026-03-01T00:00:00Z",
    ):
        self.name = name
        self.entity_type = entity_type
        self.value_type = value_type
        self.source = source
        self.description = description
        self.freshness_sla_seconds = freshness_sla_seconds
        self.is_active = is_active
        self.created_at = created_at

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "entity_type": self.entity_type,
            "value_type": self.value_type,
            "source": self.source,
            "description": self.description,
            "freshness_sla_seconds": self.freshness_sla_seconds,
            "is_active": self.is_active,
            "created_at": self.created_at,
        }


class FeatureValue:
    """A single computed feature value for an entity."""

    def __init__(
        self,
        entity_id: str,
        feature_name: str,
        value: float,
        timestamp: str = "2026-03-09T12:00:00Z",
    ):
        self.entity_id = entity_id
        self.feature_name = feature_name
        self.value = value
        self.timestamp = timestamp

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "feature_name": self.feature_name,
            "value": self.value,
            "timestamp": self.timestamp,
        }


class FeatureVector:
    """A set of feature values for a single entity."""

    def __init__(
        self,
        entity_id: str,
        features: dict,
        retrieved_at: str = "2026-03-09T12:00:00Z",
    ):
        self.entity_id = entity_id
        self.features = features
        self.retrieved_at = retrieved_at

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "features": self.features,
            "retrieved_at": self.retrieved_at,
        }
