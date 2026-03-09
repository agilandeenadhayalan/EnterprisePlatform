"""
Domain models for the Trace Collector service.
"""


class Span:
    """A single span in a distributed trace."""

    def __init__(
        self,
        id: str,
        trace_id: str,
        span_id: str,
        parent_span_id: str | None,
        operation_name: str,
        service_name: str,
        start_time: str,
        end_time: str,
        duration_ms: float,
        tags: dict,
        status: str = "ok",
    ):
        self.id = id
        self.trace_id = trace_id
        self.span_id = span_id
        self.parent_span_id = parent_span_id
        self.operation_name = operation_name
        self.service_name = service_name
        self.start_time = start_time
        self.end_time = end_time
        self.duration_ms = duration_ms
        self.tags = tags
        self.status = status

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "operation_name": self.operation_name,
            "service_name": self.service_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "tags": self.tags,
            "status": self.status,
        }


class Trace:
    """An assembled trace containing multiple spans."""

    def __init__(
        self,
        trace_id: str,
        spans: list,
        service_count: int,
        total_duration_ms: float,
        root_span: str,
    ):
        self.trace_id = trace_id
        self.spans = spans
        self.service_count = service_count
        self.total_duration_ms = total_duration_ms
        self.root_span = root_span

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "spans": [s.to_dict() if hasattr(s, "to_dict") else s for s in self.spans],
            "service_count": self.service_count,
            "total_duration_ms": self.total_duration_ms,
            "root_span": self.root_span,
        }


class ServiceDependency:
    """A dependency edge between two services."""

    def __init__(
        self,
        source_service: str,
        target_service: str,
        call_count: int,
        avg_duration_ms: float,
    ):
        self.source_service = source_service
        self.target_service = target_service
        self.call_count = call_count
        self.avg_duration_ms = avg_duration_ms

    def to_dict(self) -> dict:
        return {
            "source_service": self.source_service,
            "target_service": self.target_service,
            "call_count": self.call_count,
            "avg_duration_ms": self.avg_duration_ms,
        }
