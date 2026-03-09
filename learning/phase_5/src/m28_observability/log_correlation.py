"""
Log Correlation — linking logs to distributed traces for debugging.

WHY THIS MATTERS:
When an error occurs in production, you need to quickly answer:
"What happened before this error?" Logs alone show individual service
events. Traces alone show the request flow. Log correlation connects
the two: given an error log, find the trace. Given a trace, find all
related logs across services to reconstruct the full story.

Key concepts:
  - Correlated Log: a log entry enriched with trace_id and span_id
    so it can be linked to a specific point in a distributed trace.
  - Log-to-Trace: given an error log, find the trace_id to pull up
    the full request timeline.
  - Trace-to-Logs: given a trace_id, find all log entries across all
    services to see what happened during that request.
  - Error Context: find not just the error log, but the INFO logs
    that preceded it to understand the sequence of events.
"""


class CorrelatedLog:
    """A log entry enriched with trace context for correlation.

    In production systems like Loki or Elasticsearch, logs carry
    trace_id and span_id fields that let you jump from a log line
    directly into the Jaeger/Tempo trace view.
    """

    def __init__(
        self,
        timestamp: float,
        level: str,
        service: str,
        message: str,
        trace_id: str = None,
        span_id: str = None,
        fields: dict = None,
    ):
        self.timestamp = timestamp
        self.level = level
        self.service = service
        self.message = message
        self.trace_id = trace_id
        self.span_id = span_id
        self.fields = fields or {}

    def to_dict(self) -> dict:
        """Serialize the log entry."""
        return {
            "timestamp": self.timestamp,
            "level": self.level,
            "service": self.service,
            "message": self.message,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "fields": self.fields,
        }


class LogCorrelator:
    """Correlates logs with distributed traces for observability.

    This is the bridge between your logging pipeline and your tracing
    pipeline. When an on-call engineer sees an error alert, they:
    1. find_trace_for_error() — get the trace_id from recent errors
    2. get_error_context() — see all logs for that trace to understand
       what happened leading up to the error
    """

    def __init__(self):
        self._logs: list[CorrelatedLog] = []

    def add_log(self, log: CorrelatedLog) -> None:
        """Ingest a correlated log entry."""
        self._logs.append(log)

    def find_logs_for_trace(self, trace_id: str) -> list:
        """Find all logs associated with a specific trace.

        Returns logs sorted by timestamp, giving a chronological view
        of what happened during the traced request across all services.
        """
        matched = [log for log in self._logs if log.trace_id == trace_id]
        return sorted(matched, key=lambda l: l.timestamp)

    def find_trace_for_error(self, service: str, time_window_seconds: float = 60.0) -> str:
        """Find the trace_id associated with a recent error in a service.

        Scans ERROR-level logs for the given service and returns the
        trace_id of the most recent error log that has a trace_id.
        Only considers logs within time_window_seconds of the most
        recent log timestamp.

        Returns:
            The trace_id string, or None if no matching error is found.
        """
        if not self._logs:
            return None

        latest_timestamp = max(log.timestamp for log in self._logs)
        cutoff = latest_timestamp - time_window_seconds

        error_logs = [
            log for log in self._logs
            if log.service == service
            and log.level == "ERROR"
            and log.trace_id is not None
            and log.timestamp >= cutoff
        ]

        if not error_logs:
            return None

        # Return trace_id of the most recent error
        most_recent = max(error_logs, key=lambda l: l.timestamp)
        return most_recent.trace_id

    def get_error_context(self, trace_id: str) -> list:
        """Get all logs for a trace to understand what happened before an error.

        Returns all logs (INFO, WARN, ERROR, etc.) for the given trace_id,
        sorted by timestamp. This shows the sequence of events leading up
        to and including the error, making root cause analysis much faster.
        """
        return self.find_logs_for_trace(trace_id)

    def get_service_log_summary(self, service: str) -> dict:
        """Summarize log activity for a service.

        Returns:
            A dict with the service name, total log count, and a
            breakdown by log level (e.g. {INFO: 42, ERROR: 3}).
        """
        service_logs = [log for log in self._logs if log.service == service]
        by_level: dict[str, int] = {}
        for log in service_logs:
            by_level[log.level] = by_level.get(log.level, 0) + 1

        return {
            "service": service,
            "total": len(service_logs),
            "by_level": by_level,
        }
