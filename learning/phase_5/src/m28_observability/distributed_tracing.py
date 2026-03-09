"""
Distributed Tracing — W3C trace context propagation and span tree assembly.

WHY THIS MATTERS:
In a microservices architecture, a single user request fans out across
dozens of services. Distributed tracing stitches together the timeline
of work across all those services so you can answer: "Why was this
request slow?" and "Which service caused the error?"

Key concepts:
  - Trace: a DAG of spans representing end-to-end request processing.
  - Span: a single unit of work within a trace (e.g. an HTTP handler,
    a database query). Each span has a trace_id, its own span_id, and
    an optional parent_span_id linking it to its caller.
  - W3C Traceparent: the standard header format for propagating trace
    context across service boundaries:
      traceparent: 00-{trace_id}-{span_id}-{flags}
  - Critical Path: the longest chain of spans from root to leaf,
    representing the minimum possible latency for the trace.
"""

from enum import Enum
from uuid import uuid4


class SpanKind(Enum):
    """The role of a span within a distributed trace.

    CLIENT   — the span represents an outbound RPC or HTTP call.
    SERVER   — the span handles an inbound RPC or HTTP request.
    PRODUCER — the span enqueues a message (e.g. Kafka produce).
    CONSUMER — the span processes a dequeued message.
    INTERNAL — the span represents internal processing (no RPC).
    """

    CLIENT = "CLIENT"
    SERVER = "SERVER"
    PRODUCER = "PRODUCER"
    CONSUMER = "CONSUMER"
    INTERNAL = "INTERNAL"


class SpanEvent:
    """A timestamped annotation within a span.

    Events mark notable moments during a span's lifetime, such as
    "cache miss", "retry attempt", or "connection acquired".
    """

    def __init__(self, name: str, timestamp: float, attributes: dict = None):
        self.name = name
        self.timestamp = timestamp
        self.attributes = attributes or {}


class Span:
    """A single unit of work within a distributed trace.

    Each span captures:
    - Identity: trace_id + span_id uniquely identify it; parent_span_id
      links it to the calling span.
    - Timing: start_time and end_time in seconds since epoch.
    - Context: operation_name, service_name, tags, and events.
    - Status: "ok" or "error" indicating success or failure.

    Spans are finished by calling finish(), which records the end_time.
    Duration is computed as (end_time - start_time) in milliseconds.
    """

    def __init__(
        self,
        trace_id: str,
        span_id: str,
        operation_name: str,
        service_name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        parent_span_id: str = None,
        start_time: float = 0.0,
    ):
        self.trace_id = trace_id
        self.span_id = span_id
        self.parent_span_id = parent_span_id
        self.operation_name = operation_name
        self.service_name = service_name
        self.kind = kind
        self.start_time = start_time
        self.end_time: float = None
        self.tags: dict = {}
        self.events: list[SpanEvent] = []
        self.status: str = "ok"

    def finish(self, end_time: float = None) -> None:
        """Mark the span as finished.

        If no end_time is provided, the span's start_time + 0.1 is used
        as a default (for testing convenience).
        """
        self.end_time = end_time if end_time is not None else self.start_time + 0.1

    def add_event(self, name: str, attributes: dict = None) -> None:
        """Add a timestamped event to this span."""
        timestamp = self.start_time  # simplified: use start_time as event time
        self.events.append(SpanEvent(name, timestamp, attributes))

    def set_tag(self, key: str, value) -> None:
        """Set a key-value tag on this span for filtering and search."""
        self.tags[key] = value

    def duration_ms(self) -> float:
        """Compute span duration in milliseconds.

        Returns 0 if the span has not been finished yet.
        """
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time) * 1000.0

    def to_dict(self) -> dict:
        """Serialize the span for export to a tracing backend."""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "operation_name": self.operation_name,
            "service_name": self.service_name,
            "kind": self.kind.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms(),
            "tags": self.tags,
            "events": [{"name": e.name, "timestamp": e.timestamp, "attributes": e.attributes} for e in self.events],
            "status": self.status,
        }


class TracePropagation:
    """W3C Traceparent header injection and extraction.

    The traceparent header format is:
        {version}-{trace_id}-{span_id}-{trace_flags}

    Where:
    - version: always "00" (current spec version)
    - trace_id: 32-character lowercase hex string
    - span_id: 16-character lowercase hex string
    - trace_flags: "01" if sampled, "00" if not

    This is how trace context crosses service boundaries: the calling
    service injects the header, and the receiving service extracts it
    to continue the same trace.
    """

    @staticmethod
    def inject(trace_id: str, span_id: str, sampled: bool = True) -> str:
        """Create a W3C traceparent header value.

        Args:
            trace_id: 32-char hex string identifying the trace.
            span_id: 16-char hex string identifying the current span.
            sampled: whether the trace should be recorded.

        Returns:
            A string in the format "00-{trace_id}-{span_id}-{flags}".
        """
        flags = "01" if sampled else "00"
        return f"00-{trace_id}-{span_id}-{flags}"

    @staticmethod
    def extract(header: str) -> tuple:
        """Parse a W3C traceparent header value.

        Args:
            header: A string in "00-{trace_id}-{span_id}-{flags}" format.

        Returns:
            A tuple of (trace_id, span_id, sampled: bool).

        Raises:
            ValueError: If the header format is invalid.
        """
        parts = header.split("-")
        if len(parts) != 4:
            raise ValueError(
                f"Invalid traceparent header: expected 4 parts, got {len(parts)}: '{header}'"
            )
        version, trace_id, span_id, flags = parts
        if version != "00":
            raise ValueError(f"Unsupported traceparent version: '{version}'")
        if len(trace_id) != 32:
            raise ValueError(f"Invalid trace_id length: expected 32, got {len(trace_id)}")
        if len(span_id) != 16:
            raise ValueError(f"Invalid span_id length: expected 16, got {len(span_id)}")
        if flags not in ("00", "01"):
            raise ValueError(f"Invalid trace flags: '{flags}'")
        sampled = flags == "01"
        return trace_id, span_id, sampled


def _generate_trace_id() -> str:
    """Generate a 32-character hex trace ID."""
    return uuid4().hex


def _generate_span_id() -> str:
    """Generate a 16-character hex span ID."""
    return uuid4().hex[:16]


class TraceAssembler:
    """Assembles flat lists of spans into a hierarchical trace tree.

    In production, spans arrive out of order from different services.
    The assembler groups them by trace_id and reconstructs the parent-child
    tree structure for visualization in tools like Jaeger or Tempo.

    The critical path is the longest chain of spans from root to leaf,
    representing the minimum possible latency improvement path.
    """

    def __init__(self):
        self._spans: dict[str, list[Span]] = {}

    def add_span(self, span: Span) -> None:
        """Add a span to the assembler."""
        if span.trace_id not in self._spans:
            self._spans[span.trace_id] = []
        self._spans[span.trace_id].append(span)

    def assemble(self, trace_id: str) -> dict:
        """Assemble spans for a trace into a tree structure.

        Returns:
            A dict with 'span' (the root span) and 'children' (list of
            subtrees). Each child has the same structure recursively.

        The root span is identified as the span with no parent_span_id.
        """
        spans = self._spans.get(trace_id, [])
        if not spans:
            return {}

        # Build lookup: span_id -> span
        span_map = {s.span_id: s for s in spans}
        # Build children lookup: parent_span_id -> [child spans]
        children_map: dict[str, list[Span]] = {}
        root = None
        for s in spans:
            if s.parent_span_id is None:
                root = s
            else:
                if s.parent_span_id not in children_map:
                    children_map[s.parent_span_id] = []
                children_map[s.parent_span_id].append(s)

        if root is None:
            return {}

        def build_tree(span: Span) -> dict:
            children = children_map.get(span.span_id, [])
            return {
                "span": span,
                "children": [build_tree(child) for child in children],
            }

        return build_tree(root)

    def get_critical_path(self, trace_id: str) -> list:
        """Find the critical path — the longest duration chain from root to leaf.

        The critical path determines the minimum latency of the trace.
        Optimizing spans on this path yields the most latency improvement.

        Returns:
            A list of Span objects from root to leaf along the longest path.
        """
        tree = self.assemble(trace_id)
        if not tree:
            return []

        def find_longest_path(node: dict) -> list:
            span = node["span"]
            children = node["children"]
            if not children:
                return [span]
            longest = []
            for child in children:
                path = find_longest_path(child)
                child_duration = sum(s.duration_ms() for s in path)
                longest_duration = sum(s.duration_ms() for s in longest)
                if child_duration > longest_duration:
                    longest = path
            return [span] + longest

        return find_longest_path(tree)
