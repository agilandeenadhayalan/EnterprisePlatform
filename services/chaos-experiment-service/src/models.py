"""
Domain models for the Chaos Experiment service.
"""


class ChaosExperiment:
    """A chaos experiment definition."""

    def __init__(
        self,
        id: str,
        name: str,
        experiment_type: str,
        target_service: str,
        blast_radius: str,
        duration_seconds: int,
        status: str,
        created_at: str,
        parameters: dict | None = None,
    ):
        self.id = id
        self.name = name
        self.experiment_type = experiment_type
        self.target_service = target_service
        self.blast_radius = blast_radius
        self.duration_seconds = duration_seconds
        self.status = status
        self.created_at = created_at
        self.parameters = parameters or {}

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "experiment_type": self.experiment_type,
            "target_service": self.target_service,
            "blast_radius": self.blast_radius,
            "duration_seconds": self.duration_seconds,
            "status": self.status,
            "created_at": self.created_at,
            "parameters": self.parameters,
        }


class ChaosRun:
    """A run of a chaos experiment."""

    def __init__(
        self,
        id: str,
        experiment_id: str,
        started_at: str,
        ended_at: str | None = None,
        steady_state_before: dict | None = None,
        steady_state_after: dict | None = None,
        result: str = "pending",
        impact_summary: dict | None = None,
    ):
        self.id = id
        self.experiment_id = experiment_id
        self.started_at = started_at
        self.ended_at = ended_at
        self.steady_state_before = steady_state_before or {}
        self.steady_state_after = steady_state_after or {}
        self.result = result
        self.impact_summary = impact_summary or {}

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "experiment_id": self.experiment_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "steady_state_before": self.steady_state_before,
            "steady_state_after": self.steady_state_after,
            "result": self.result,
            "impact_summary": self.impact_summary,
        }


class SteadyStateHypothesis:
    """A steady state hypothesis for a chaos experiment."""

    def __init__(
        self,
        id: str,
        experiment_id: str,
        metric_name: str,
        operator: str,
        threshold: float,
        description: str,
    ):
        self.id = id
        self.experiment_id = experiment_id
        self.metric_name = metric_name
        self.operator = operator
        self.threshold = threshold
        self.description = description

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "experiment_id": self.experiment_id,
            "metric_name": self.metric_name,
            "operator": self.operator,
            "threshold": self.threshold,
            "description": self.description,
        }
