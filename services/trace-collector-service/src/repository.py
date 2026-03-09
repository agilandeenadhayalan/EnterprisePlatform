"""
In-memory trace collector repository with pre-seeded data.
"""

import uuid
from datetime import datetime, timezone, timedelta

from models import Span, Trace, ServiceDependency


class TraceCollectorRepository:
    """In-memory store for spans, traces, and service dependencies."""

    def __init__(self, seed: bool = False):
        self.spans: list[Span] = []
        self.dependencies: list[ServiceDependency] = []
        if seed:
            self._seed()

    def _seed(self):
        now = datetime.now(timezone.utc)

        # Trace 1: api-gateway -> auth-service -> postgres (ride request flow)
        t1_start = (now - timedelta(minutes=30)).isoformat()
        t1_mid1 = (now - timedelta(minutes=30) + timedelta(milliseconds=5)).isoformat()
        t1_mid2 = (now - timedelta(minutes=30) + timedelta(milliseconds=15)).isoformat()
        t1_mid3 = (now - timedelta(minutes=30) + timedelta(milliseconds=25)).isoformat()
        t1_end = (now - timedelta(minutes=30) + timedelta(milliseconds=45)).isoformat()
        self.spans.extend([
            Span("s-001", "trace-001", "span-001", None, "POST /api/v1/rides", "api-gateway", t1_start, t1_end, 45.0, {"http.method": "POST", "http.url": "/api/v1/rides"}, "ok"),
            Span("s-002", "trace-001", "span-002", "span-001", "authenticate", "auth-service", t1_mid1, t1_mid2, 10.0, {"auth.method": "jwt"}, "ok"),
            Span("s-003", "trace-001", "span-003", "span-002", "SELECT users", "postgres", t1_mid1, (now - timedelta(minutes=30) + timedelta(milliseconds=10)).isoformat(), 5.0, {"db.type": "postgresql"}, "ok"),
        ])

        # Trace 2: api-gateway -> ride-service -> driver-matching -> notification-service (ride dispatch)
        t2_start = (now - timedelta(minutes=25)).isoformat()
        t2_end = (now - timedelta(minutes=25) + timedelta(milliseconds=120)).isoformat()
        self.spans.extend([
            Span("s-004", "trace-002", "span-004", None, "POST /api/v1/dispatch", "api-gateway", t2_start, t2_end, 120.0, {"http.method": "POST"}, "ok"),
            Span("s-005", "trace-002", "span-005", "span-004", "find_driver", "ride-service", (now - timedelta(minutes=25) + timedelta(milliseconds=5)).isoformat(), (now - timedelta(minutes=25) + timedelta(milliseconds=80)).isoformat(), 75.0, {"ride.type": "standard"}, "ok"),
            Span("s-006", "trace-002", "span-006", "span-005", "match_nearest", "driver-matching", (now - timedelta(minutes=25) + timedelta(milliseconds=10)).isoformat(), (now - timedelta(minutes=25) + timedelta(milliseconds=60)).isoformat(), 50.0, {"algorithm": "nearest"}, "ok"),
            Span("s-007", "trace-002", "span-007", "span-004", "notify_driver", "notification-service", (now - timedelta(minutes=25) + timedelta(milliseconds=85)).isoformat(), (now - timedelta(minutes=25) + timedelta(milliseconds=110)).isoformat(), 25.0, {"channel": "push"}, "ok"),
        ])

        # Trace 3: api-gateway -> payment-service -> postgres (payment processing)
        t3_start = (now - timedelta(minutes=20)).isoformat()
        t3_end = (now - timedelta(minutes=20) + timedelta(milliseconds=200)).isoformat()
        self.spans.extend([
            Span("s-008", "trace-003", "span-008", None, "POST /api/v1/payments", "api-gateway", t3_start, t3_end, 200.0, {"http.method": "POST"}, "ok"),
            Span("s-009", "trace-003", "span-009", "span-008", "process_payment", "payment-service", (now - timedelta(minutes=20) + timedelta(milliseconds=10)).isoformat(), (now - timedelta(minutes=20) + timedelta(milliseconds=180)).isoformat(), 170.0, {"payment.method": "card"}, "ok"),
            Span("s-010", "trace-003", "span-010", "span-009", "INSERT payments", "postgres", (now - timedelta(minutes=20) + timedelta(milliseconds=15)).isoformat(), (now - timedelta(minutes=20) + timedelta(milliseconds=30)).isoformat(), 15.0, {"db.type": "postgresql"}, "ok"),
        ])

        # Trace 4: api-gateway -> user-service -> auth-service -> redis (user profile)
        t4_start = (now - timedelta(minutes=15)).isoformat()
        t4_end = (now - timedelta(minutes=15) + timedelta(milliseconds=60)).isoformat()
        self.spans.extend([
            Span("s-011", "trace-004", "span-011", None, "GET /api/v1/users/me", "api-gateway", t4_start, t4_end, 60.0, {"http.method": "GET"}, "ok"),
            Span("s-012", "trace-004", "span-012", "span-011", "get_profile", "user-service", (now - timedelta(minutes=15) + timedelta(milliseconds=5)).isoformat(), (now - timedelta(minutes=15) + timedelta(milliseconds=50)).isoformat(), 45.0, {"cache": "miss"}, "ok"),
            Span("s-013", "trace-004", "span-013", "span-012", "validate_token", "auth-service", (now - timedelta(minutes=15) + timedelta(milliseconds=8)).isoformat(), (now - timedelta(minutes=15) + timedelta(milliseconds=18)).isoformat(), 10.0, {"token.type": "bearer"}, "ok"),
            Span("s-014", "trace-004", "span-014", "span-013", "GET session", "redis", (now - timedelta(minutes=15) + timedelta(milliseconds=10)).isoformat(), (now - timedelta(minutes=15) + timedelta(milliseconds=13)).isoformat(), 3.0, {"db.type": "redis"}, "ok"),
        ])

        # Trace 5: kafka-consumer -> analytics-service -> clickhouse (event processing)
        t5_start = (now - timedelta(minutes=10)).isoformat()
        t5_end = (now - timedelta(minutes=10) + timedelta(milliseconds=80)).isoformat()
        self.spans.extend([
            Span("s-015", "trace-005", "span-015", None, "consume_events", "kafka-consumer", t5_start, t5_end, 80.0, {"topic": "ride-events"}, "ok"),
            Span("s-016", "trace-005", "span-016", "span-015", "process_batch", "analytics-service", (now - timedelta(minutes=10) + timedelta(milliseconds=5)).isoformat(), (now - timedelta(minutes=10) + timedelta(milliseconds=70)).isoformat(), 65.0, {"batch.size": "100"}, "ok"),
            Span("s-017", "trace-005", "span-017", "span-016", "INSERT events", "clickhouse", (now - timedelta(minutes=10) + timedelta(milliseconds=10)).isoformat(), (now - timedelta(minutes=10) + timedelta(milliseconds=40)).isoformat(), 30.0, {"db.type": "clickhouse"}, "error"),
        ])

        # 8 service dependencies derived from traces
        self.dependencies = [
            ServiceDependency("api-gateway", "auth-service", 15, 12.5),
            ServiceDependency("api-gateway", "ride-service", 8, 85.0),
            ServiceDependency("api-gateway", "payment-service", 12, 180.0),
            ServiceDependency("api-gateway", "user-service", 20, 45.0),
            ServiceDependency("ride-service", "driver-matching", 8, 55.0),
            ServiceDependency("ride-service", "notification-service", 6, 28.0),
            ServiceDependency("auth-service", "postgres", 30, 6.0),
            ServiceDependency("payment-service", "postgres", 12, 18.0),
        ]

    # ── Submit Span ──

    def submit_span(self, data: dict) -> Span:
        span_id_internal = f"s-{uuid.uuid4().hex[:8]}"
        start = data["start_time"]
        end = data["end_time"]
        # Calculate duration
        try:
            st = datetime.fromisoformat(start.replace("Z", "+00:00"))
            et = datetime.fromisoformat(end.replace("Z", "+00:00"))
            duration_ms = (et - st).total_seconds() * 1000
        except Exception:
            duration_ms = 0.0

        span = Span(
            id=span_id_internal,
            trace_id=data["trace_id"],
            span_id=data["span_id"],
            parent_span_id=data.get("parent_span_id"),
            operation_name=data["operation_name"],
            service_name=data["service_name"],
            start_time=start,
            end_time=end,
            duration_ms=round(duration_ms, 1),
            tags=data.get("tags", {}),
            status=data.get("status", "ok"),
        )
        self.spans.append(span)
        return span

    # ── Get Trace ──

    def get_trace(self, trace_id: str) -> Trace | None:
        trace_spans = [s for s in self.spans if s.trace_id == trace_id]
        if not trace_spans:
            return None
        # Sort by start_time
        trace_spans.sort(key=lambda s: s.start_time)
        root = next((s for s in trace_spans if s.parent_span_id is None), trace_spans[0])
        services = {s.service_name for s in trace_spans}
        total_duration = root.duration_ms
        return Trace(
            trace_id=trace_id,
            spans=trace_spans,
            service_count=len(services),
            total_duration_ms=total_duration,
            root_span=root.operation_name,
        )

    # ── List Traces ──

    def list_traces(self) -> list[dict]:
        trace_ids = list(dict.fromkeys(s.trace_id for s in self.spans))
        summaries = []
        for tid in trace_ids:
            trace = self.get_trace(tid)
            if trace:
                root_spans = [s for s in trace.spans if s.parent_span_id is None]
                root = root_spans[0] if root_spans else trace.spans[0]
                summaries.append({
                    "trace_id": tid,
                    "root_operation": trace.root_span,
                    "service_count": trace.service_count,
                    "duration_ms": trace.total_duration_ms,
                    "start_time": root.start_time,
                })
        return summaries

    # ── Get Spans ──

    def get_spans(self, trace_id: str) -> list[Span]:
        spans = [s for s in self.spans if s.trace_id == trace_id]
        spans.sort(key=lambda s: s.start_time)
        return spans

    # ── Dependencies ──

    def get_dependencies(self) -> list[ServiceDependency]:
        return list(self.dependencies)

    # ── Analyze ──

    def analyze_service(self, service_name: str) -> dict | None:
        service_spans = [s for s in self.spans if s.service_name == service_name]
        if not service_spans:
            return None
        durations = sorted([s.duration_ms for s in service_spans])
        errors = sum(1 for s in service_spans if s.status == "error")
        p50_idx = min(int(len(durations) * 0.5), len(durations) - 1)
        p99_idx = min(int(len(durations) * 0.99), len(durations) - 1)
        return {
            "service_name": service_name,
            "span_count": len(service_spans),
            "avg_duration_ms": round(sum(durations) / len(durations), 2),
            "p50_ms": durations[p50_idx],
            "p99_ms": durations[p99_idx],
            "error_rate": round(errors / len(service_spans), 4),
        }

    # ── Stats ──

    def get_stats(self) -> dict:
        trace_ids = set(s.trace_id for s in self.spans)
        services = set(s.service_name for s in self.spans)
        error_count = sum(1 for s in self.spans if s.status == "error")
        avg_spans = len(self.spans) / len(trace_ids) if trace_ids else 0.0
        return {
            "total_traces": len(trace_ids),
            "total_spans": len(self.spans),
            "unique_services": len(services),
            "avg_spans_per_trace": round(avg_spans, 2),
            "error_span_count": error_count,
        }


REPO_CLASS = TraceCollectorRepository
repo = TraceCollectorRepository(seed=True)
