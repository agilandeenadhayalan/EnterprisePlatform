"""
In-memory metrics aggregation repository with pre-seeded data.
"""

import uuid
from datetime import datetime, timezone, timedelta

from models import MetricDefinition, MetricDataPoint, RecordingRule


class MetricsAggregationRepository:
    """In-memory store for metric definitions, data points, and recording rules."""

    def __init__(self, seed: bool = False):
        self.definitions: dict[str, MetricDefinition] = {}
        self.data_points: list[MetricDataPoint] = []
        self.recording_rules: list[RecordingRule] = []
        if seed:
            self._seed()

    def _seed(self):
        now = datetime.now(timezone.utc)

        defs = [
            MetricDefinition("met-001", "http_requests_total", "counter", "Total HTTP requests", ["service", "method", "status"], "requests"),
            MetricDefinition("met-002", "http_request_duration_seconds", "histogram", "HTTP request duration", ["service", "method"], "seconds"),
            MetricDefinition("met-003", "cpu_usage_percent", "gauge", "CPU usage percentage", ["service", "instance"], "percent"),
            MetricDefinition("met-004", "memory_usage_bytes", "gauge", "Memory usage in bytes", ["service", "instance"], "bytes"),
            MetricDefinition("met-005", "active_connections", "gauge", "Active connections count", ["service"], "connections"),
            MetricDefinition("met-006", "error_count_total", "counter", "Total error count", ["service", "error_type"], "errors"),
            MetricDefinition("met-007", "request_queue_depth", "gauge", "Request queue depth", ["service"], "requests"),
            MetricDefinition("met-008", "disk_io_bytes_total", "counter", "Total disk I/O bytes", ["service", "direction"], "bytes"),
            MetricDefinition("met-009", "gc_pause_seconds", "histogram", "GC pause duration", ["service"], "seconds"),
            MetricDefinition("met-010", "cache_hit_ratio", "gauge", "Cache hit ratio", ["service", "cache_name"], "ratio"),
            MetricDefinition("met-011", "kafka_consumer_lag", "gauge", "Kafka consumer lag", ["consumer_group", "topic"], "messages"),
            MetricDefinition("met-012", "db_query_duration_seconds", "histogram", "Database query duration", ["service", "query_type"], "seconds"),
        ]
        for d in defs:
            self.definitions[d.name] = d

        # 50 data points across metrics with various labels
        services = ["auth-service", "user-service", "payment-service"]
        methods = ["GET", "POST"]
        statuses = ["200", "500"]
        dp_id = 0
        points = []

        for i in range(15):
            dp_id += 1
            ts = (now - timedelta(minutes=50 - i)).isoformat()
            svc = services[i % 3]
            method = methods[i % 2]
            status = statuses[0] if i % 5 != 0 else statuses[1]
            points.append(MetricDataPoint(f"dp-{dp_id:03d}", "http_requests_total", {"service": svc, "method": method, "status": status}, float(100 + i * 10), ts))

        for i in range(10):
            dp_id += 1
            ts = (now - timedelta(minutes=40 - i)).isoformat()
            svc = services[i % 3]
            method = methods[i % 2]
            points.append(MetricDataPoint(f"dp-{dp_id:03d}", "http_request_duration_seconds", {"service": svc, "method": method}, round(0.05 + i * 0.02, 3), ts))

        for i in range(10):
            dp_id += 1
            ts = (now - timedelta(minutes=30 - i)).isoformat()
            svc = services[i % 3]
            points.append(MetricDataPoint(f"dp-{dp_id:03d}", "cpu_usage_percent", {"service": svc, "instance": f"inst-{i % 3}"}, round(30.0 + i * 5.5, 1), ts))

        for i in range(5):
            dp_id += 1
            ts = (now - timedelta(minutes=20 - i)).isoformat()
            svc = services[i % 3]
            points.append(MetricDataPoint(f"dp-{dp_id:03d}", "error_count_total", {"service": svc, "error_type": "timeout" if i % 2 == 0 else "internal"}, float(i + 1), ts))

        for i in range(5):
            dp_id += 1
            ts = (now - timedelta(minutes=15 - i)).isoformat()
            svc = services[i % 3]
            points.append(MetricDataPoint(f"dp-{dp_id:03d}", "memory_usage_bytes", {"service": svc, "instance": f"inst-{i % 2}"}, float(512_000_000 + i * 64_000_000), ts))

        for i in range(5):
            dp_id += 1
            ts = (now - timedelta(minutes=10 - i)).isoformat()
            svc = services[i % 3]
            points.append(MetricDataPoint(f"dp-{dp_id:03d}", "active_connections", {"service": svc}, float(50 + i * 15), ts))

        self.data_points.extend(points)

        rules = [
            RecordingRule("rr-001", "request_rate_5m", "rate(http_requests_total[5m])", 300, "http_request_rate_5m"),
            RecordingRule("rr-002", "error_rate_5m", "rate(error_count_total[5m])", 300, "error_rate_5m"),
            RecordingRule("rr-003", "p99_latency", "histogram_quantile(0.99, http_request_duration_seconds)", 300, "http_p99_latency"),
            RecordingRule("rr-004", "avg_cpu", "avg(cpu_usage_percent)", 60, "cpu_avg_usage"),
        ]
        self.recording_rules.extend(rules)

    # ── Definitions ──

    def list_definitions(self) -> list[MetricDefinition]:
        return list(self.definitions.values())

    def get_definition(self, name: str) -> MetricDefinition | None:
        return self.definitions.get(name)

    def create_definition(self, data: dict) -> MetricDefinition:
        def_id = f"met-{uuid.uuid4().hex[:8]}"
        md = MetricDefinition(
            id=def_id,
            name=data["name"],
            metric_type=data["metric_type"],
            description=data["description"],
            labels=data.get("labels", []),
            unit=data.get("unit", ""),
        )
        self.definitions[md.name] = md
        return md

    # ── Ingest ──

    def ingest_data_point(self, data: dict) -> MetricDataPoint:
        dp_id = f"dp-{uuid.uuid4().hex[:8]}"
        ts = data.get("timestamp") or datetime.now(timezone.utc).isoformat()
        dp = MetricDataPoint(
            id=dp_id,
            metric_name=data["metric_name"],
            labels=data.get("labels", {}),
            value=data["value"],
            timestamp=ts,
        )
        self.data_points.append(dp)
        return dp

    # ── Query ──

    def query(self, metric_name: str, labels: dict | None = None, time_start: str | None = None, time_end: str | None = None) -> list[MetricDataPoint]:
        results = [dp for dp in self.data_points if dp.metric_name == metric_name]
        if labels:
            filtered = []
            for dp in results:
                match = all(dp.labels.get(k) == v for k, v in labels.items())
                if match:
                    filtered.append(dp)
            results = filtered
        if time_start:
            results = [dp for dp in results if dp.timestamp >= time_start]
        if time_end:
            results = [dp for dp in results if dp.timestamp <= time_end]
        return results

    # ── Aggregate ──

    def aggregate(self, metric_name: str, function: str, labels: dict | None = None, percentile: float | None = None) -> float:
        points = self.query(metric_name, labels)
        values = [p.value for p in points]
        if not values:
            return 0.0

        if function == "sum":
            return round(sum(values), 4)
        elif function == "avg":
            return round(sum(values) / len(values), 4)
        elif function == "min":
            return round(min(values), 4)
        elif function == "max":
            return round(max(values), 4)
        elif function == "count":
            return float(len(values))
        elif function == "rate":
            if len(values) < 2:
                return 0.0
            return round((values[-1] - values[0]) / len(values), 4)
        elif function == "percentile":
            p = percentile or 99.0
            sorted_vals = sorted(values)
            idx = int(len(sorted_vals) * p / 100.0)
            idx = min(idx, len(sorted_vals) - 1)
            return round(sorted_vals[idx], 4)
        else:
            return 0.0

    # ── Recording Rules ──

    def list_recording_rules(self) -> list[RecordingRule]:
        return list(self.recording_rules)

    def create_recording_rule(self, data: dict) -> RecordingRule:
        rr_id = f"rr-{uuid.uuid4().hex[:8]}"
        rr = RecordingRule(
            id=rr_id,
            name=data["name"],
            expression=data["expression"],
            interval_seconds=data.get("interval_seconds", 300),
            destination_metric=data["destination_metric"],
        )
        self.recording_rules.append(rr)
        return rr

    # ── Stats ──

    def get_stats(self) -> dict:
        by_type: dict[str, int] = {}
        for d in self.definitions.values():
            by_type[d.metric_type] = by_type.get(d.metric_type, 0) + 1
        return {
            "total_definitions": len(self.definitions),
            "total_data_points": len(self.data_points),
            "by_type": by_type,
        }


REPO_CLASS = MetricsAggregationRepository
repo = MetricsAggregationRepository(seed=True)
