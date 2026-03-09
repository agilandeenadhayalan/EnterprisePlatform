"""
Domain models for the Log Aggregation service.
"""


class LogEntry:
    """A single log entry."""

    def __init__(
        self,
        id: str,
        timestamp: str,
        service_name: str,
        level: str,
        message: str,
        trace_id: str | None = None,
        span_id: str | None = None,
        fields: dict | None = None,
    ):
        self.id = id
        self.timestamp = timestamp
        self.service_name = service_name
        self.level = level
        self.message = message
        self.trace_id = trace_id
        self.span_id = span_id
        self.fields = fields or {}

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "service_name": self.service_name,
            "level": self.level,
            "message": self.message,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "fields": self.fields,
        }


class LogPattern:
    """A detected log pattern."""

    def __init__(
        self,
        id: str,
        pattern: str,
        count: int,
        first_seen: str,
        last_seen: str,
        sample_message: str,
    ):
        self.id = id
        self.pattern = pattern
        self.count = count
        self.first_seen = first_seen
        self.last_seen = last_seen
        self.sample_message = sample_message

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "pattern": self.pattern,
            "count": self.count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "sample_message": self.sample_message,
        }


class RetentionPolicy:
    """A log retention policy."""

    def __init__(
        self,
        id: str,
        name: str,
        service_filter: str,
        level_filter: str,
        retention_days: int,
        is_active: bool = True,
    ):
        self.id = id
        self.name = name
        self.service_filter = service_filter
        self.level_filter = level_filter
        self.retention_days = retention_days
        self.is_active = is_active

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "service_filter": self.service_filter,
            "level_filter": self.level_filter,
            "retention_days": self.retention_days,
            "is_active": self.is_active,
        }
