"""
Domain models for the Experiment Analytics service.
"""


class ExperimentAnalysis:
    """An experiment analysis result."""

    def __init__(
        self,
        id: str,
        experiment_id: str,
        metric_name: str,
        control_mean: float,
        variant_mean: float,
        p_value: float,
        significant: bool,
        effect_size: float,
        sample_size: int,
        created_at: str = "2026-03-01T00:00:00Z",
    ):
        self.id = id
        self.experiment_id = experiment_id
        self.metric_name = metric_name
        self.control_mean = control_mean
        self.variant_mean = variant_mean
        self.p_value = p_value
        self.significant = significant
        self.effect_size = effect_size
        self.sample_size = sample_size
        self.created_at = created_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "experiment_id": self.experiment_id,
            "metric_name": self.metric_name,
            "control_mean": self.control_mean,
            "variant_mean": self.variant_mean,
            "p_value": self.p_value,
            "significant": self.significant,
            "effect_size": self.effect_size,
            "sample_size": self.sample_size,
            "created_at": self.created_at,
        }


class SegmentAnalysis:
    """Segment-level analysis result."""

    def __init__(
        self,
        segment_name: str,
        control_mean: float,
        variant_mean: float,
        lift: float,
        significant: bool,
    ):
        self.segment_name = segment_name
        self.control_mean = control_mean
        self.variant_mean = variant_mean
        self.lift = lift
        self.significant = significant

    def to_dict(self) -> dict:
        return {
            "segment_name": self.segment_name,
            "control_mean": self.control_mean,
            "variant_mean": self.variant_mean,
            "lift": self.lift,
            "significant": self.significant,
        }


class AnalysisReport:
    """A comprehensive analysis report."""

    def __init__(
        self,
        id: str,
        experiment_id: str,
        analyses: list[dict],
        segments: list[dict],
        recommendation: str,
        created_at: str = "2026-03-01T00:00:00Z",
    ):
        self.id = id
        self.experiment_id = experiment_id
        self.analyses = analyses
        self.segments = segments
        self.recommendation = recommendation
        self.created_at = created_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "experiment_id": self.experiment_id,
            "analyses": self.analyses,
            "segments": self.segments,
            "recommendation": self.recommendation,
            "created_at": self.created_at,
        }
