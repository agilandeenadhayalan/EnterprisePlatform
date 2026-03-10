"""
Domain models for the Experiment service.
"""


class Experiment:
    """An experiment definition."""

    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        experiment_type: str,
        status: str,
        variants: list[dict],
        targeting_rules: list[dict],
        traffic_percentage: float,
        created_at: str = "2026-03-01T00:00:00Z",
        updated_at: str = "2026-03-01T00:00:00Z",
    ):
        self.id = id
        self.name = name
        self.description = description
        self.experiment_type = experiment_type
        self.status = status
        self.variants = variants
        self.targeting_rules = targeting_rules
        self.traffic_percentage = traffic_percentage
        self.created_at = created_at
        self.updated_at = updated_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "experiment_type": self.experiment_type,
            "status": self.status,
            "variants": self.variants,
            "targeting_rules": self.targeting_rules,
            "traffic_percentage": self.traffic_percentage,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class ExperimentVariant:
    """A variant within an experiment."""

    def __init__(self, name: str, weight: float, config: dict):
        self.name = name
        self.weight = weight
        self.config = config

    def to_dict(self) -> dict:
        return {"name": self.name, "weight": self.weight, "config": self.config}


class TargetingRule:
    """A targeting rule for experiment traffic."""

    def __init__(self, attribute: str, operator: str, value: str):
        self.attribute = attribute
        self.operator = operator
        self.value = value

    def to_dict(self) -> dict:
        return {"attribute": self.attribute, "operator": self.operator, "value": self.value}
