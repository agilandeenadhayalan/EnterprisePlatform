"""
Structured JSON logging with trace correlation.

This module provides structured logging that outputs machine-parseable log
entries (dictionaries) rather than free-form text strings. Each log entry
carries a fixed schema (timestamp, level, service, message) plus optional
trace correlation fields and arbitrary key-value metadata.

Why Structured Logging?
-----------------------
Traditional text logs (e.g., ``"2024-01-15 ERROR: failed to connect"``) are
easy to read on a terminal but difficult to search, filter, and aggregate
at scale. Structured logs emit each entry as a dictionary (typically
serialized to JSON), making them first-class data that can be:

- **Indexed** by any field (level, service, trace_id, custom fields)
- **Correlated** with distributed traces via trace_id/span_id
- **Aggregated** in log management systems (ELK, Loki, Datadog)
- **Alerted on** using structured queries rather than regex patterns

Trace Correlation
-----------------
Every log entry can optionally carry a ``trace_id`` and ``span_id``. When
these fields are populated, the log entry can be linked to the exact
distributed trace that produced it, enabling operators to jump from a log
message directly to the full request trace in their observability platform.

Usage Example
-------------
    logger = StructuredLogger("trip-service", environment="production")

    # Basic logging
    logger.info("Service started", port=8080)

    # Logging with trace correlation
    logger.info(
        "Trip created",
        trace_id="abc123",
        span_id="def456",
        trip_id="trip-789",
        user_id="user-42",
    )

    # Retrieve entries for analysis
    errors = logger.get_entries(level="error")
    trace_logs = logger.get_entries(trace_id="abc123")
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class LogEntry:
    """A single structured log record.

    Each ``LogEntry`` represents one log event with a fixed set of core
    fields and an extensible ``fields`` dictionary for application-specific
    metadata.

    Parameters
    ----------
    timestamp : str
        ISO 8601 formatted timestamp of when the log event occurred.
    level : str
        The severity level (e.g., "info", "warn", "error", "debug").
    service : str
        The name of the service that produced this log entry.
    message : str
        A human-readable description of the event.
    trace_id : str, optional
        The distributed trace ID for correlation with tracing systems.
    span_id : str, optional
        The span ID within the trace for finer-grained correlation.
    fields : dict, optional
        Arbitrary key-value metadata (e.g., user_id, request_path, duration).
    """

    def __init__(
        self,
        timestamp: str,
        level: str,
        service: str,
        message: str,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        fields: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.timestamp = timestamp
        self.level = level
        self.service = service
        self.message = message
        self.trace_id = trace_id
        self.span_id = span_id
        self.fields = fields or {}

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the log entry to a dictionary suitable for JSON output.

        Returns
        -------
        dict
            A flat dictionary containing all log entry fields. The ``fields``
            sub-dictionary is included as a nested object to avoid key
            collisions with core fields.
        """
        entry: Dict[str, Any] = {
            "timestamp": self.timestamp,
            "level": self.level,
            "service": self.service,
            "message": self.message,
        }
        if self.trace_id is not None:
            entry["trace_id"] = self.trace_id
        if self.span_id is not None:
            entry["span_id"] = self.span_id
        if self.fields:
            entry["fields"] = self.fields
        return entry

    def __repr__(self) -> str:
        return (
            f"LogEntry(level={self.level!r}, service={self.service!r}, "
            f"message={self.message!r})"
        )


class StructuredLogger:
    """A structured logger that produces machine-parseable log entries.

    The ``StructuredLogger`` creates ``LogEntry`` instances with consistent
    formatting and stores them for later retrieval. It supports trace
    correlation by accepting ``trace_id`` and ``span_id`` as keyword
    arguments on any log method.

    Default fields (set at construction time) are merged into every log
    entry, providing a convenient way to attach service-wide metadata like
    environment, region, or version.

    Parameters
    ----------
    service_name : str
        The name of the service producing logs. This is included in every
        log entry for multi-service log aggregation.
    **default_fields
        Additional key-value pairs to include in every log entry. Useful
        for environment, version, region, etc.

    Usage Example
    -------------
        logger = StructuredLogger("trip-service", env="prod", version="1.2.3")
        logger.info("Startup complete", port=8080)
        logger.error("Database timeout", trace_id="abc", db="clickhouse")
    """

    def __init__(self, service_name: str, **default_fields: Any) -> None:
        self.service_name = service_name
        self._default_fields: Dict[str, Any] = default_fields
        self._entries: List[LogEntry] = []

    def _log(self, level: str, message: str, **kwargs: Any) -> LogEntry:
        """Internal method that creates and stores a log entry.

        Parameters
        ----------
        level : str
            The log severity level.
        message : str
            The log message.
        **kwargs
            Optional ``trace_id``, ``span_id``, and any additional fields.

        Returns
        -------
        LogEntry
            The created log entry.
        """
        trace_id = kwargs.pop("trace_id", None)
        span_id = kwargs.pop("span_id", None)

        # Merge default fields with per-call fields; per-call fields take
        # precedence over defaults when keys collide.
        merged_fields = {**self._default_fields, **kwargs}

        entry = LogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=level,
            service=self.service_name,
            message=message,
            trace_id=trace_id,
            span_id=span_id,
            fields=merged_fields if merged_fields else {},
        )

        self._entries.append(entry)
        return entry

    def info(self, message: str, **kwargs: Any) -> LogEntry:
        """Log an informational message.

        Info-level logs record normal operational events: service startup,
        configuration loaded, request served, etc.

        Parameters
        ----------
        message : str
            The log message.
        **kwargs
            Optional trace_id, span_id, and additional fields.

        Returns
        -------
        LogEntry
            The created log entry.
        """
        return self._log("info", message, **kwargs)

    def warn(self, message: str, **kwargs: Any) -> LogEntry:
        """Log a warning message.

        Warning-level logs indicate potential problems that do not prevent
        the system from functioning but may require attention: deprecated
        API usage, approaching resource limits, retry attempts, etc.

        Parameters
        ----------
        message : str
            The log message.
        **kwargs
            Optional trace_id, span_id, and additional fields.

        Returns
        -------
        LogEntry
            The created log entry.
        """
        return self._log("warn", message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> LogEntry:
        """Log an error message.

        Error-level logs indicate failures that affect the current operation
        but do not crash the service: failed database queries, invalid input,
        downstream service unavailability, etc.

        Parameters
        ----------
        message : str
            The log message.
        **kwargs
            Optional trace_id, span_id, and additional fields.

        Returns
        -------
        LogEntry
            The created log entry.
        """
        return self._log("error", message, **kwargs)

    def debug(self, message: str, **kwargs: Any) -> LogEntry:
        """Log a debug message.

        Debug-level logs provide detailed diagnostic information useful during
        development and troubleshooting. They are typically disabled in
        production due to their high volume.

        Parameters
        ----------
        message : str
            The log message.
        **kwargs
            Optional trace_id, span_id, and additional fields.

        Returns
        -------
        LogEntry
            The created log entry.
        """
        return self._log("debug", message, **kwargs)

    def get_entries(
        self,
        level: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> List[LogEntry]:
        """Retrieve stored log entries with optional filtering.

        Parameters
        ----------
        level : str, optional
            If provided, only return entries matching this severity level.
        trace_id : str, optional
            If provided, only return entries associated with this trace ID.

        Returns
        -------
        list of LogEntry
            The filtered log entries, in chronological order.
        """
        results = self._entries
        if level is not None:
            results = [e for e in results if e.level == level]
        if trace_id is not None:
            results = [e for e in results if e.trace_id == trace_id]
        return results

    def clear(self) -> None:
        """Remove all stored log entries.

        This is useful for testing or when entries have been flushed to an
        external log aggregation system and are no longer needed in memory.
        """
        self._entries.clear()

    def __repr__(self) -> str:
        return (
            f"StructuredLogger(service={self.service_name!r}, "
            f"entries={len(self._entries)})"
        )
