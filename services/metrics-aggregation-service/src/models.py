"""
Domain models for the Metrics Aggregation service.
"""


class MetricDefinition:
    """Metadata describing a registered metric."""

    def __init__(
        self,
        id: str,
        name: str,
        metric_type: str,
        description: str,
        labels: list[str],
        unit: str = "",
    ):
        self.id = id
        self.name = name
        self.metric_type = metric_type
        self.description = description
        self.labels = labels
        self.unit = unit

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "metric_type": self.metric_type,
            "description": self.description,
            "labels": self.labels,
            "unit": self.unit,
        }


class MetricDataPoint:
    """A single metric data point."""

    def __init__(
        self,
        id: str,
        metric_name: str,
        labels: dict,
        value: float,
        timestamp: str,
    ):
        self.id = id
        self.metric_name = metric_name
        self.labels = labels
        self.value = value
        self.timestamp = timestamp

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "metric_name": self.metric_name,
            "labels": self.labels,
            "value": self.value,
            "timestamp": self.timestamp,
        }


class RecordingRule:
    """A recording rule that precomputes metric aggregations."""

    def __init__(
        self,
        id: str,
        name: str,
        expression: str,
        interval_seconds: int,
        destination_metric: str,
    ):
        self.id = id
        self.name = name
        self.expression = expression
        self.interval_seconds = interval_seconds
        self.destination_metric = destination_metric

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "expression": self.expression,
            "interval_seconds": self.interval_seconds,
            "destination_metric": self.destination_metric,
        }
