"""
Distributed tracing with W3C Trace Context propagation.

This module implements the core primitives for distributed tracing, enabling
operators to follow a single request as it traverses multiple services in
the platform. Each request gets a unique **trace ID**, and each unit of work
within that request gets a **span**.

Key Concepts
------------
- **Trace**: The end-to-end journey of a request through the system, identified
  by a globally unique ``trace_id``. A trace is composed of one or more spans.

- **Span**: A named, timed operation within a trace (e.g., "HTTP GET /api/trips",
  "query ClickHouse", "publish Kafka event"). Spans form a tree structure via
  parent-child relationships, allowing operators to see exactly where time is
  spent and where errors occur.

- **Trace Context**: The minimal set of identifiers (trace_id, span_id) that
  must be propagated between services so that spans can be correlated into a
  single trace. This module uses the W3C ``traceparent`` header format
  (https://www.w3.org/TR/trace-context/).

W3C traceparent Format
----------------------
The ``traceparent`` header has the format::

    {version}-{trace_id}-{span_id}-{trace_flags}

Example::

    00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01

- ``version``: always "00" (current spec version)
- ``trace_id``: 32 hex characters (128-bit)
- ``span_id``: 16 hex characters (64-bit)
- ``trace_flags``: 2 hex characters ("01" = sampled)

Usage Example
-------------
    tracer = TracingClient()

    # Start a root span (new trace)
    span, ctx = tracer.start_span("handle_request", "trip-service")

    # Propagate context to downstream service via HTTP header
    headers = {"traceparent": ctx.to_traceparent()}

    # In the downstream service, continue the trace
    parent_ctx = TraceContext.from_traceparent(headers["traceparent"])
    child_span, child_ctx = tracer.start_span(
        "query_database", "trip-service", parent_context=parent_ctx
    )

    # Finish spans when work is done
    tracer.finish_span(child_span)
    tracer.finish_span(span)

    # Inspect the full trace
    trace = tracer.get_trace(ctx.trace_id)
"""

from __future__ import annotations

import time
import uuid
from typing import Dict, List, Optional, Tuple


class Span:
    """A single unit of work within a distributed trace.

    A span captures the timing and metadata of an operation. Spans are
    organized in a parent-child tree within a trace: the root span has no
    parent, and child spans reference their parent via ``parent_span_id``.

    Span Lifecycle
    --------------
    1. Created by ``TracingClient.start_span()`` -- ``start_time`` is recorded.
    2. Tags and status can be added during execution.
    3. ``finish()`` is called when the operation completes -- ``end_time`` is set.

    Parameters
    ----------
    trace_id : str
        The 32-character hex trace identifier.
    span_id : str
        The 16-character hex span identifier.
    parent_span_id : str or None
        The span ID of the parent span, or ``None`` for root spans.
    operation_name : str
        A human-readable name for the operation (e.g., "GET /api/trips").
    service_name : str
        The name of the service executing this span.
    """

    def __init__(
        self,
        trace_id: str,
        span_id: str,
        parent_span_id: Optional[str],
        operation_name: str,
        service_name: str,
    ) -> None:
        self.trace_id = trace_id
        self.span_id = span_id
        self.parent_span_id = parent_span_id
        self.operation_name = operation_name
        self.service_name = service_name
        self.start_time: float = time.time()
        self.end_time: Optional[float] = None
        self.tags: Dict[str, str] = {}
        self.status: str = "ok"

    def finish(self) -> None:
        """Mark the span as complete by recording the end time.

        Once finished, ``duration_ms()`` will return a valid duration.
        Calling ``finish()`` multiple times overwrites the previous end time.
        """
        self.end_time = time.time()

    def set_tag(self, key: str, value: str) -> None:
        """Attach a key-value tag to the span for filtering and annotation.

        Tags are indexed metadata that monitoring systems use for filtering
        and grouping spans. Common tags include ``http.method``,
        ``http.status_code``, ``db.type``, ``error``, etc.

        Parameters
        ----------
        key : str
            The tag key.
        value : str
            The tag value.
        """
        self.tags[key] = value

    def set_status(self, status: str) -> None:
        """Set the span's completion status.

        Parameters
        ----------
        status : str
            The status string. Common values: "ok", "error", "cancelled".
        """
        self.status = status

    def duration_ms(self) -> Optional[float]:
        """Calculate the span duration in milliseconds.

        Returns
        -------
        float or None
            Duration in milliseconds if the span has been finished,
            ``None`` otherwise.
        """
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time) * 1000.0

    def to_dict(self) -> Dict:
        """Serialize the span to a dictionary.

        Returns
        -------
        dict
            Complete span data including trace/span IDs, timing, tags, and
            status.
        """
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "operation_name": self.operation_name,
            "service_name": self.service_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms(),
            "tags": self.tags,
            "status": self.status,
        }

    def __repr__(self) -> str:
        return (
            f"Span(operation={self.operation_name!r}, "
            f"service={self.service_name!r}, "
            f"trace_id={self.trace_id[:8]}..., "
            f"status={self.status!r})"
        )


class TraceContext:
    """Carries trace identity across service boundaries.

    ``TraceContext`` is the minimal payload that must be propagated between
    services (e.g., via HTTP headers) to correlate spans into a single trace.
    It supports serialization to and from the W3C ``traceparent`` header
    format.

    Parameters
    ----------
    trace_id : str
        The 32-character hex trace identifier.
    span_id : str
        The 16-character hex span identifier of the current (or parent) span.
    """

    def __init__(self, trace_id: str, span_id: str) -> None:
        self.trace_id = trace_id
        self.span_id = span_id

    def to_traceparent(self) -> str:
        """Serialize to a W3C traceparent header value.

        Format: ``00-{trace_id}-{span_id}-01``

        The version is always "00" and the trace flags are "01" (sampled).

        Returns
        -------
        str
            The traceparent header string.
        """
        return f"00-{self.trace_id}-{self.span_id}-01"

    @classmethod
    def from_traceparent(cls, header: str) -> TraceContext:
        """Parse a W3C traceparent header into a TraceContext.

        Parameters
        ----------
        header : str
            A traceparent header value in the format
            ``{version}-{trace_id}-{span_id}-{trace_flags}``.

        Returns
        -------
        TraceContext
            The parsed trace context.

        Raises
        ------
        ValueError
            If the header does not match the expected format.
        """
        parts = header.strip().split("-")
        if len(parts) != 4:
            raise ValueError(
                f"Invalid traceparent header: expected 4 dash-separated "
                f"parts, got {len(parts)}. Header: {header!r}"
            )
        _version, trace_id, span_id, _flags = parts
        return cls(trace_id=trace_id, span_id=span_id)

    def __repr__(self) -> str:
        return f"TraceContext(trace_id={self.trace_id[:8]}..., span_id={self.span_id})"


class TracingClient:
    """Manages the creation and collection of distributed trace spans.

    The ``TracingClient`` is the primary interface for application code to
    create spans and build trace trees. It handles ID generation, parent-child
    linking, and span storage.

    Trace Construction
    ------------------
    - **Root span**: Call ``start_span()`` without a ``parent_context``. A new
      trace ID is generated automatically.
    - **Child span**: Call ``start_span()`` with the ``parent_context`` from
      an existing span. The child inherits the parent's trace ID and records
      the parent's span ID for tree reconstruction.

    Usage Example
    -------------
        tracer = TracingClient()

        # Root span
        root_span, root_ctx = tracer.start_span("handle_request", "api-gateway")

        # Child span within the same trace
        db_span, db_ctx = tracer.start_span(
            "query_users", "api-gateway", parent_context=root_ctx
        )
        tracer.finish_span(db_span)
        tracer.finish_span(root_span)
    """

    def __init__(self) -> None:
        self._spans: Dict[str, List[Span]] = {}

    def start_span(
        self,
        operation_name: str,
        service_name: str,
        parent_context: Optional[TraceContext] = None,
    ) -> Tuple[Span, TraceContext]:
        """Begin a new span, optionally linking it to a parent trace.

        Parameters
        ----------
        operation_name : str
            A descriptive name for the operation being traced.
        service_name : str
            The name of the service executing the operation.
        parent_context : TraceContext, optional
            The trace context from a parent span. If provided, the new span
            inherits the parent's trace ID. If omitted, a new trace is started.

        Returns
        -------
        tuple of (Span, TraceContext)
            The newly created span and a trace context that should be
            propagated to any downstream calls.
        """
        if parent_context is not None:
            trace_id = parent_context.trace_id
            parent_span_id = parent_context.span_id
        else:
            trace_id = uuid.uuid4().hex  # 32 hex chars
            parent_span_id = None

        span_id = uuid.uuid4().hex[:16]  # 16 hex chars

        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            service_name=service_name,
        )

        if trace_id not in self._spans:
            self._spans[trace_id] = []
        self._spans[trace_id].append(span)

        ctx = TraceContext(trace_id=trace_id, span_id=span_id)
        return span, ctx

    def finish_span(self, span: Span) -> None:
        """Finish a span by recording its end time.

        This is a convenience method that delegates to ``span.finish()``.
        It exists so that all span lifecycle management can flow through
        the tracing client.

        Parameters
        ----------
        span : Span
            The span to finish.
        """
        span.finish()

    def get_trace(self, trace_id: str) -> List[Span]:
        """Retrieve all spans belonging to a trace.

        Parameters
        ----------
        trace_id : str
            The 32-character hex trace identifier.

        Returns
        -------
        list of Span
            All spans recorded under the given trace ID, in creation order.
            Returns an empty list if the trace ID is unknown.
        """
        return self._spans.get(trace_id, [])

    def get_active_spans(self) -> List[Span]:
        """Return all spans that have not yet been finished.

        Active spans are those where ``end_time`` is still ``None``. A large
        number of active spans may indicate resource leaks (spans that were
        never properly finished).

        Returns
        -------
        list of Span
            Unfinished spans across all traces.
        """
        active: List[Span] = []
        for spans in self._spans.values():
            for span in spans:
                if span.end_time is None:
                    active.append(span)
        return active

    def __repr__(self) -> str:
        total = sum(len(spans) for spans in self._spans.values())
        return f"TracingClient(traces={len(self._spans)}, spans={total})"
