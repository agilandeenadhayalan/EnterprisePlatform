"""
Domain models for the AB Test Analytics service.
"""


class ABTestResult:
    """Result of an A/B test statistical analysis."""

    def __init__(
        self,
        id: str,
        experiment_id: str,
        metric: str,
        control_count: int,
        control_conversions: int,
        variant_count: int,
        variant_conversions: int,
        z_score: float,
        p_value: float,
        significant: bool,
        created_at: str = "2026-03-01T00:00:00Z",
    ):
        self.id = id
        self.experiment_id = experiment_id
        self.metric = metric
        self.control_count = control_count
        self.control_conversions = control_conversions
        self.variant_count = variant_count
        self.variant_conversions = variant_conversions
        self.z_score = z_score
        self.p_value = p_value
        self.significant = significant
        self.created_at = created_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "experiment_id": self.experiment_id,
            "metric": self.metric,
            "control_count": self.control_count,
            "control_conversions": self.control_conversions,
            "variant_count": self.variant_count,
            "variant_conversions": self.variant_conversions,
            "z_score": self.z_score,
            "p_value": self.p_value,
            "significant": self.significant,
            "created_at": self.created_at,
        }


class PowerCalculation:
    """Result of a power/sample size calculation."""

    def __init__(
        self,
        sample_size_needed: int,
        power: float,
        alpha: float,
        minimum_detectable_effect: float,
    ):
        self.sample_size_needed = sample_size_needed
        self.power = power
        self.alpha = alpha
        self.minimum_detectable_effect = minimum_detectable_effect

    def to_dict(self) -> dict:
        return {
            "sample_size_needed": self.sample_size_needed,
            "power": self.power,
            "alpha": self.alpha,
            "minimum_detectable_effect": self.minimum_detectable_effect,
        }


class SequentialTestResult:
    """Result of a sequential test analysis."""

    def __init__(
        self,
        id: str,
        experiment_id: str,
        observations: int,
        current_z: float,
        boundary: float,
        stopped_early: bool,
        created_at: str = "2026-03-01T00:00:00Z",
    ):
        self.id = id
        self.experiment_id = experiment_id
        self.observations = observations
        self.current_z = current_z
        self.boundary = boundary
        self.stopped_early = stopped_early
        self.created_at = created_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "experiment_id": self.experiment_id,
            "observations": self.observations,
            "current_z": self.current_z,
            "boundary": self.boundary,
            "stopped_early": self.stopped_early,
            "created_at": self.created_at,
        }
