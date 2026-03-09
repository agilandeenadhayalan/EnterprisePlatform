"""
Domain models for the Feature Pipeline Driver service.
"""


class DriverFeatureSet:
    """Computed feature set for a single driver."""

    def __init__(
        self,
        driver_id: str,
        features: dict,
        computed_at: str = "2026-03-09T12:00:00Z",
    ):
        self.driver_id = driver_id
        self.features = features
        self.computed_at = computed_at

    def to_dict(self) -> dict:
        return {
            "driver_id": self.driver_id,
            "features": self.features,
            "computed_at": self.computed_at,
        }


class PipelineRun:
    """Record of a pipeline execution."""

    def __init__(
        self,
        id: str,
        status: str,
        start_time: str,
        end_time: str | None = None,
        features_computed: int = 0,
    ):
        self.id = id
        self.status = status
        self.start_time = start_time
        self.end_time = end_time
        self.features_computed = features_computed

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "status": self.status,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "features_computed": self.features_computed,
        }
