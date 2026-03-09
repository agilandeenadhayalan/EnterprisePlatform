"""
Tests for M28: Observability Stack — Metrics, tracing, log correlation,
and alerting rules.
"""

import pytest

from m28_observability.metrics_types import Counter, Gauge, Histogram, Summary
from m28_observability.distributed_tracing import (
    SpanKind,
    SpanEvent,
    Span,
    TracePropagation,
    TraceAssembler,
)
from m28_observability.log_correlation import CorrelatedLog, LogCorrelator
from m28_observability.alerting_rules import (
    AlertSeverity,
    AlertState,
    AlertRule,
    AlertEvaluator,
    RoutingPolicy,
    SilenceRule,
)


# ── Counter ──


class TestCounter:
    def test_inc(self):
        """Counter starts at 0 and increments by 1 by default."""
        c = Counter("requests_total")
        c.inc()
        assert c.get() == 1.0

    def test_get_initial(self):
        """Counter starts at 0."""
        c = Counter("requests_total")
        assert c.get() == 0.0

    def test_inc_by_amount(self):
        """Counter can be incremented by a specific positive amount."""
        c = Counter("bytes_sent", labels={"method": "GET"})
        c.inc(100.5)
        assert c.get() == 100.5

    def test_inc_negative_raises(self):
        """Counter rejects negative increments (monotonicity)."""
        c = Counter("requests_total")
        with pytest.raises(ValueError, match="positive"):
            c.inc(-1)

    def test_inc_zero_raises(self):
        """Counter rejects zero increments."""
        c = Counter("requests_total")
        with pytest.raises(ValueError, match="positive"):
            c.inc(0)

    def test_reset_raises(self):
        """Counters cannot be reset by user code."""
        c = Counter("requests_total")
        c.inc()
        with pytest.raises(ValueError, match="cannot be reset"):
            c.reset()

    def test_to_dict(self):
        """Counter serializes correctly."""
        c = Counter("http_requests", labels={"method": "POST"})
        c.inc(5)
        d = c.to_dict()
        assert d["name"] == "http_requests"
        assert d["type"] == "counter"
        assert d["value"] == 5.0
        assert d["labels"] == {"method": "POST"}


# ── Gauge ──


class TestGauge:
    def test_set(self):
        """Gauge can be set to an arbitrary value."""
        g = Gauge("temperature")
        g.set(42.5)
        assert g.get() == 42.5

    def test_inc(self):
        """Gauge increments from its current value."""
        g = Gauge("in_flight_requests")
        g.set(10)
        g.inc()
        assert g.get() == 11

    def test_dec(self):
        """Gauge decrements from its current value."""
        g = Gauge("in_flight_requests")
        g.set(10)
        g.dec(3)
        assert g.get() == 7

    def test_to_dict(self):
        """Gauge serializes correctly."""
        g = Gauge("memory_usage_mb", labels={"host": "web-1"})
        g.set(512)
        d = g.to_dict()
        assert d["name"] == "memory_usage_mb"
        assert d["type"] == "gauge"
        assert d["value"] == 512
        assert d["labels"] == {"host": "web-1"}


# ── Histogram ──


class TestHistogram:
    def test_observe(self):
        """Histogram records observations."""
        h = Histogram("request_duration_seconds")
        h.observe(0.1)
        h.observe(0.5)
        assert h.get_count() == 2

    def test_bucket_counts(self):
        """Bucket counts are cumulative."""
        h = Histogram("latency", buckets=[0.1, 0.5, 1.0, float("inf")])
        h.observe(0.05)
        h.observe(0.2)
        h.observe(0.8)
        h.observe(2.0)
        buckets = h.get_bucket_counts()
        assert buckets[0.1] == 1    # only 0.05
        assert buckets[0.5] == 2    # 0.05 + 0.2
        assert buckets[1.0] == 3    # 0.05 + 0.2 + 0.8
        assert buckets[float("inf")] == 4  # all

    def test_percentile_50(self):
        """50th percentile (median) of [1,2,3,4,5] should be 3."""
        h = Histogram("latency", buckets=[10, float("inf")])
        for v in [1, 2, 3, 4, 5]:
            h.observe(v)
        assert h.get_percentile(50) == 3.0

    def test_percentile_99(self):
        """99th percentile of 100 values [0..99] should be near 98."""
        h = Histogram("latency", buckets=[100, float("inf")])
        for v in range(100):
            h.observe(v)
        p99 = h.get_percentile(99)
        assert 97 <= p99 <= 99

    def test_percentile_empty_raises(self):
        """Cannot compute percentile with no observations."""
        h = Histogram("latency")
        with pytest.raises(ValueError, match="no observations"):
            h.get_percentile(50)

    def test_mean(self):
        """Mean of [2, 4, 6] should be 4."""
        h = Histogram("latency")
        for v in [2, 4, 6]:
            h.observe(v)
        assert h.get_mean() == 4.0

    def test_mean_empty(self):
        """Mean of empty histogram returns 0."""
        h = Histogram("latency")
        assert h.get_mean() == 0.0

    def test_count_sum(self):
        """Count and sum are tracked correctly."""
        h = Histogram("latency")
        h.observe(1.0)
        h.observe(2.0)
        h.observe(3.0)
        assert h.get_count() == 3
        assert h.get_sum() == 6.0


# ── Summary ──


class TestSummary:
    def test_observe(self):
        """Summary records observations."""
        s = Summary("response_time")
        s.observe(0.1)
        s.observe(0.2)
        assert s.get_count() == 2
        assert s.get_sum() == pytest.approx(0.3)

    def test_quantile_median(self):
        """0.5 quantile of [1,2,3,4,5] should be 3."""
        s = Summary("latency")
        for v in [1, 2, 3, 4, 5]:
            s.observe(v)
        assert s.get_quantile(0.5) == 3.0

    def test_quantile_99(self):
        """0.99 quantile of 100 values should be near the top."""
        s = Summary("latency")
        for v in range(100):
            s.observe(v)
        q99 = s.get_quantile(0.99)
        assert 97 <= q99 <= 99

    def test_window(self):
        """Quantiles use only the last _max_age_observations entries."""
        s = Summary("latency", max_age_observations=5)
        # First add 100 large values
        for _ in range(100):
            s.observe(1000)
        # Then add 5 small values
        for v in [1, 2, 3, 4, 5]:
            s.observe(v)
        # The window should only see [1,2,3,4,5]
        assert s.get_quantile(0.5) == 3.0


# ── Span ──


class TestSpan:
    def test_creation(self):
        """Span is created with correct fields."""
        span = Span(
            trace_id="a" * 32,
            span_id="b" * 16,
            operation_name="GET /api/users",
            service_name="user-service",
            kind=SpanKind.SERVER,
            start_time=1000.0,
        )
        assert span.trace_id == "a" * 32
        assert span.operation_name == "GET /api/users"
        assert span.kind == SpanKind.SERVER
        assert span.status == "ok"
        assert span.end_time is None

    def test_finish_sets_end_time(self):
        """Finishing a span records the end time."""
        span = Span("a" * 32, "b" * 16, "op", "svc", start_time=1000.0)
        span.finish(1001.0)
        assert span.end_time == 1001.0

    def test_duration_ms(self):
        """Duration is computed in milliseconds."""
        span = Span("a" * 32, "b" * 16, "op", "svc", start_time=1.0)
        span.finish(1.5)
        assert span.duration_ms() == 500.0

    def test_duration_unfinished(self):
        """Unfinished span has duration 0."""
        span = Span("a" * 32, "b" * 16, "op", "svc", start_time=1.0)
        assert span.duration_ms() == 0.0

    def test_add_event(self):
        """Events can be added to a span."""
        span = Span("a" * 32, "b" * 16, "op", "svc", start_time=1.0)
        span.add_event("cache_miss", {"key": "user:42"})
        assert len(span.events) == 1
        assert span.events[0].name == "cache_miss"
        assert span.events[0].attributes == {"key": "user:42"}

    def test_to_dict(self):
        """Span serializes correctly."""
        span = Span("a" * 32, "b" * 16, "op", "svc", start_time=1.0)
        span.set_tag("http.status_code", 200)
        span.finish(1.5)
        d = span.to_dict()
        assert d["trace_id"] == "a" * 32
        assert d["duration_ms"] == 500.0
        assert d["tags"]["http.status_code"] == 200
        assert d["status"] == "ok"


# ── TracePropagation ──


class TestTracePropagation:
    def test_inject_sampled(self):
        """Sampled trace produces trace-flags 01."""
        header = TracePropagation.inject("a" * 32, "b" * 16, sampled=True)
        assert header == f"00-{'a' * 32}-{'b' * 16}-01"

    def test_inject_unsampled(self):
        """Unsampled trace produces trace-flags 00."""
        header = TracePropagation.inject("a" * 32, "b" * 16, sampled=False)
        assert header == f"00-{'a' * 32}-{'b' * 16}-00"

    def test_extract_valid(self):
        """Valid traceparent header is correctly parsed."""
        header = f"00-{'a' * 32}-{'b' * 16}-01"
        trace_id, span_id, sampled = TracePropagation.extract(header)
        assert trace_id == "a" * 32
        assert span_id == "b" * 16
        assert sampled is True

    def test_extract_invalid_raises(self):
        """Invalid traceparent header raises ValueError."""
        with pytest.raises(ValueError, match="Invalid"):
            TracePropagation.extract("invalid-header")

    def test_roundtrip(self):
        """Inject then extract preserves all fields."""
        tid = "c" * 32
        sid = "d" * 16
        header = TracePropagation.inject(tid, sid, sampled=True)
        extracted_tid, extracted_sid, extracted_sampled = TracePropagation.extract(header)
        assert extracted_tid == tid
        assert extracted_sid == sid
        assert extracted_sampled is True


# ── TraceAssembler ──


class TestTraceAssembler:
    def _make_trace(self):
        """Build a simple 3-span trace: root -> child1 -> grandchild."""
        assembler = TraceAssembler()
        tid = "a" * 32
        root = Span(tid, "root0000root0000", "entry", "gateway", start_time=0)
        root.finish(10.0)
        child = Span(tid, "child000child000", "db_query", "db-svc",
                     parent_span_id="root0000root0000", start_time=1.0)
        child.finish(8.0)
        grandchild = Span(tid, "grand000grand000", "cache_get", "cache-svc",
                          parent_span_id="child000child000", start_time=2.0)
        grandchild.finish(3.0)
        assembler.add_span(root)
        assembler.add_span(child)
        assembler.add_span(grandchild)
        return assembler, tid

    def test_add_spans(self):
        """Spans are added without error."""
        assembler, tid = self._make_trace()
        # Should not raise
        tree = assembler.assemble(tid)
        assert tree is not None

    def test_assemble_tree(self):
        """Assembled tree has correct parent-child structure."""
        assembler, tid = self._make_trace()
        tree = assembler.assemble(tid)
        assert tree["span"].operation_name == "entry"
        assert len(tree["children"]) == 1
        assert tree["children"][0]["span"].operation_name == "db_query"
        assert len(tree["children"][0]["children"]) == 1
        assert tree["children"][0]["children"][0]["span"].operation_name == "cache_get"

    def test_root_span_found(self):
        """The root span (no parent) is correctly identified."""
        assembler, tid = self._make_trace()
        tree = assembler.assemble(tid)
        assert tree["span"].parent_span_id is None

    def test_critical_path(self):
        """Critical path follows the longest duration chain."""
        assembler, tid = self._make_trace()
        path = assembler.get_critical_path(tid)
        assert len(path) == 3
        assert path[0].operation_name == "entry"
        assert path[1].operation_name == "db_query"
        assert path[2].operation_name == "cache_get"

    def test_empty_trace(self):
        """Assembling a nonexistent trace returns empty dict."""
        assembler = TraceAssembler()
        assert assembler.assemble("nonexistent") == {}


# ── LogCorrelator ──


class TestLogCorrelator:
    def test_add_log(self):
        """Logs can be added to the correlator."""
        lc = LogCorrelator()
        log = CorrelatedLog(1000.0, "INFO", "auth-svc", "Login succeeded", trace_id="t1")
        lc.add_log(log)
        assert len(lc._logs) == 1

    def test_find_logs_for_trace(self):
        """Find all logs for a specific trace sorted by time."""
        lc = LogCorrelator()
        lc.add_log(CorrelatedLog(1002.0, "ERROR", "db-svc", "Timeout", trace_id="t1"))
        lc.add_log(CorrelatedLog(1001.0, "INFO", "auth-svc", "Checking creds", trace_id="t1"))
        lc.add_log(CorrelatedLog(1000.0, "INFO", "gateway", "Request received", trace_id="t1"))
        lc.add_log(CorrelatedLog(1005.0, "INFO", "other", "Unrelated", trace_id="t2"))

        logs = lc.find_logs_for_trace("t1")
        assert len(logs) == 3
        assert logs[0].timestamp < logs[1].timestamp < logs[2].timestamp

    def test_find_trace_for_error(self):
        """Find trace_id from a recent ERROR log for a service."""
        lc = LogCorrelator()
        lc.add_log(CorrelatedLog(1000.0, "INFO", "db-svc", "Query started", trace_id="t1"))
        lc.add_log(CorrelatedLog(1001.0, "ERROR", "db-svc", "Connection refused", trace_id="t1"))
        lc.add_log(CorrelatedLog(1002.0, "INFO", "db-svc", "Retrying", trace_id="t1"))

        trace_id = lc.find_trace_for_error("db-svc")
        assert trace_id == "t1"

    def test_find_trace_for_error_none(self):
        """Returns None if no ERROR logs exist for the service."""
        lc = LogCorrelator()
        lc.add_log(CorrelatedLog(1000.0, "INFO", "db-svc", "All good", trace_id="t1"))

        assert lc.find_trace_for_error("db-svc") is None

    def test_error_context(self):
        """Error context returns all logs for the trace sorted by time."""
        lc = LogCorrelator()
        lc.add_log(CorrelatedLog(1000.0, "INFO", "gateway", "Request received", trace_id="t1"))
        lc.add_log(CorrelatedLog(1001.0, "INFO", "auth-svc", "Auth OK", trace_id="t1"))
        lc.add_log(CorrelatedLog(1002.0, "ERROR", "db-svc", "Timeout", trace_id="t1"))

        context = lc.get_error_context("t1")
        assert len(context) == 3
        assert context[0].message == "Request received"
        assert context[2].message == "Timeout"

    def test_service_log_summary(self):
        """Summary counts logs by level for a service."""
        lc = LogCorrelator()
        lc.add_log(CorrelatedLog(1.0, "INFO", "web", "req 1"))
        lc.add_log(CorrelatedLog(2.0, "INFO", "web", "req 2"))
        lc.add_log(CorrelatedLog(3.0, "ERROR", "web", "crash"))
        lc.add_log(CorrelatedLog(4.0, "INFO", "other", "unrelated"))

        summary = lc.get_service_log_summary("web")
        assert summary["service"] == "web"
        assert summary["total"] == 3
        assert summary["by_level"]["INFO"] == 2
        assert summary["by_level"]["ERROR"] == 1


# ── AlertEvaluator ──


class TestAlertEvaluator:
    def test_condition_not_met_inactive(self):
        """Alert is INACTIVE when condition is not met."""
        rule = AlertRule("HighCPU", "cpu > 90", 90, "gt", AlertSeverity.CRITICAL)
        evaluator = AlertEvaluator()
        assert evaluator.evaluate(rule, 50) == AlertState.INACTIVE

    def test_condition_met_no_duration_firing(self):
        """Alert fires immediately when for_duration is 0."""
        rule = AlertRule("HighCPU", "cpu > 90", 90, "gt", AlertSeverity.CRITICAL,
                         for_duration_seconds=0)
        evaluator = AlertEvaluator()
        assert evaluator.evaluate(rule, 95) == AlertState.FIRING

    def test_condition_met_pending(self):
        """Alert is PENDING when condition met but duration not reached."""
        rule = AlertRule("HighCPU", "cpu > 90", 90, "gt", AlertSeverity.WARNING,
                         for_duration_seconds=300)
        evaluator = AlertEvaluator()
        assert evaluator.evaluate(rule, 95, duration_active=100) == AlertState.PENDING

    def test_condition_met_firing_after_duration(self):
        """Alert FIRES after the for_duration window is exceeded."""
        rule = AlertRule("HighCPU", "cpu > 90", 90, "gt", AlertSeverity.CRITICAL,
                         for_duration_seconds=300)
        evaluator = AlertEvaluator()
        assert evaluator.evaluate(rule, 95, duration_active=300) == AlertState.FIRING

    def test_operator_gt(self):
        """Greater-than operator works correctly."""
        evaluator = AlertEvaluator()
        assert evaluator._check_condition(91, "gt", 90) is True
        assert evaluator._check_condition(90, "gt", 90) is False

    def test_operator_lt(self):
        """Less-than operator works correctly."""
        evaluator = AlertEvaluator()
        assert evaluator._check_condition(5, "lt", 10) is True
        assert evaluator._check_condition(10, "lt", 10) is False

    def test_operator_gte(self):
        """Greater-than-or-equal operator works correctly."""
        evaluator = AlertEvaluator()
        assert evaluator._check_condition(90, "gte", 90) is True
        assert evaluator._check_condition(89, "gte", 90) is False

    def test_operator_lte(self):
        """Less-than-or-equal operator works correctly."""
        evaluator = AlertEvaluator()
        assert evaluator._check_condition(10, "lte", 10) is True
        assert evaluator._check_condition(11, "lte", 10) is False


# ── RoutingPolicy ──


class TestRoutingPolicy:
    def test_add_route(self):
        """Routes can be added for a severity level."""
        rp = RoutingPolicy()
        rp.add_route(AlertSeverity.CRITICAL, "pagerduty")
        assert rp.get_channels(AlertSeverity.CRITICAL) == ["pagerduty"]

    def test_multiple_channels(self):
        """Multiple channels can be registered for the same severity."""
        rp = RoutingPolicy()
        rp.add_route(AlertSeverity.CRITICAL, "pagerduty")
        rp.add_route(AlertSeverity.CRITICAL, "slack-oncall")
        assert len(rp.get_channels(AlertSeverity.CRITICAL)) == 2

    def test_route_firing_alert(self):
        """FIRING alerts are routed to the correct channels."""
        rp = RoutingPolicy()
        rp.add_route(AlertSeverity.CRITICAL, "pagerduty")
        rp.add_route(AlertSeverity.WARNING, "slack")
        rule = AlertRule("HighCPU", "cpu > 90", 90, "gt", AlertSeverity.CRITICAL)
        channels = rp.route_alert(rule, AlertState.FIRING)
        assert channels == ["pagerduty"]

    def test_route_non_firing_empty(self):
        """Non-FIRING alerts return empty channel list."""
        rp = RoutingPolicy()
        rp.add_route(AlertSeverity.CRITICAL, "pagerduty")
        rule = AlertRule("HighCPU", "cpu > 90", 90, "gt", AlertSeverity.CRITICAL)
        assert rp.route_alert(rule, AlertState.PENDING) == []
        assert rp.route_alert(rule, AlertState.INACTIVE) == []


# ── SilenceRule ──


class TestSilenceRule:
    def test_matches(self):
        """Silence matches when all matchers match the alert rule."""
        silence = SilenceRule("maint", {"name": "HighCPU"}, 1000, 2000)
        rule = AlertRule("HighCPU", "cpu > 90", 90, "gt", AlertSeverity.CRITICAL)
        assert silence.matches(rule) is True

    def test_matches_severity(self):
        """Silence can match on severity enum value."""
        silence = SilenceRule("maint", {"severity": "critical"}, 1000, 2000)
        rule = AlertRule("HighCPU", "cpu > 90", 90, "gt", AlertSeverity.CRITICAL)
        assert silence.matches(rule) is True

    def test_no_match(self):
        """Silence does not match when matchers don't align."""
        silence = SilenceRule("maint", {"name": "LowDisk"}, 1000, 2000)
        rule = AlertRule("HighCPU", "cpu > 90", 90, "gt", AlertSeverity.CRITICAL)
        assert silence.matches(rule) is False

    def test_is_active(self):
        """Silence is active within its time window."""
        silence = SilenceRule("maint", {}, 1000, 2000)
        assert silence.is_active(1500) is True

    def test_is_expired(self):
        """Silence is not active after its end time."""
        silence = SilenceRule("maint", {}, 1000, 2000)
        assert silence.is_active(2500) is False

    def test_not_yet_active(self):
        """Silence is not active before its start time."""
        silence = SilenceRule("maint", {}, 1000, 2000)
        assert silence.is_active(500) is False
