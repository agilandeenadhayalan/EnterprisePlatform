"""
Domain models for the RL Model Serving service.
"""


class RLModel:
    """An RL model registered for serving."""

    def __init__(
        self,
        id: str,
        name: str,
        version: str,
        algorithm: str,
        status: str,
        metrics: dict,
        created_at: str = "2026-03-01T00:00:00Z",
        updated_at: str = "2026-03-01T00:00:00Z",
    ):
        self.id = id
        self.name = name
        self.version = version
        self.algorithm = algorithm
        self.status = status
        self.metrics = metrics
        self.created_at = created_at
        self.updated_at = updated_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "algorithm": self.algorithm,
            "status": self.status,
            "metrics": self.metrics,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class ModelPrediction:
    """A prediction made by a model."""

    def __init__(
        self,
        id: str,
        model_id: str,
        state_input: dict,
        action_output: str,
        confidence: float,
        latency_ms: float,
        created_at: str = "2026-03-01T00:00:00Z",
    ):
        self.id = id
        self.model_id = model_id
        self.state_input = state_input
        self.action_output = action_output
        self.confidence = confidence
        self.latency_ms = latency_ms
        self.created_at = created_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "model_id": self.model_id,
            "state_input": self.state_input,
            "action_output": self.action_output,
            "confidence": self.confidence,
            "latency_ms": self.latency_ms,
            "created_at": self.created_at,
        }


class ModelComparison:
    """A comparison between two models."""

    def __init__(
        self,
        model_a_id: str,
        model_b_id: str,
        metric: str,
        model_a_value: float,
        model_b_value: float,
        winner: str,
    ):
        self.model_a_id = model_a_id
        self.model_b_id = model_b_id
        self.metric = metric
        self.model_a_value = model_a_value
        self.model_b_value = model_b_value
        self.winner = winner

    def to_dict(self) -> dict:
        return {
            "model_a_id": self.model_a_id,
            "model_b_id": self.model_b_id,
            "metric": self.metric,
            "model_a_value": self.model_a_value,
            "model_b_value": self.model_b_value,
            "winner": self.winner,
        }
