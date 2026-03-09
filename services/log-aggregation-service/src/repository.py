"""
In-memory log aggregation repository with pre-seeded data.
"""

import uuid
from datetime import datetime, timezone, timedelta

from models import LogEntry, LogPattern, RetentionPolicy


class LogAggregationRepository:
    """In-memory store for log entries, patterns, and retention policies."""

    def __init__(self, seed: bool = False):
        self.entries: list[LogEntry] = []
        self.patterns: list[LogPattern] = []
        self.retention_policies: list[RetentionPolicy] = []
        if seed:
            self._seed()

    def _seed(self):
        now = datetime.now(timezone.utc)

        services = ["auth-service", "user-service", "payment-service", "ride-service", "notification-service"]
        entry_id = 0

        # 10 INFO entries
        info_messages = [
            "Request processed successfully",
            "User login completed",
            "Cache refreshed",
            "Health check passed",
            "Configuration reloaded",
            "Session created for user",
            "Database connection pool initialized",
            "Message published to kafka",
            "Scheduled job completed",
            "Metrics exported successfully",
        ]
        for i in range(10):
            entry_id += 1
            ts = (now - timedelta(minutes=60 - i)).isoformat()
            svc = services[i % 5]
            trace = f"trace-{i:04d}" if i < 4 else None
            span = f"span-{i:04d}" if i < 4 else None
            self.entries.append(LogEntry(
                f"log-{entry_id:03d}", ts, svc, "INFO", info_messages[i],
                trace, span, {"request_id": f"req-{i:03d}"},
            ))

        # 8 WARN entries
        warn_messages = [
            "Connection timeout to redis",
            "Slow query detected: 2.3s",
            "Rate limit approaching threshold",
            "Connection timeout to postgres",
            "Retry attempt 2 for payment processing",
            "High memory usage detected: 82%",
            "Connection timeout to kafka",
            "Deprecated API version used",
        ]
        for i in range(8):
            entry_id += 1
            ts = (now - timedelta(minutes=50 - i)).isoformat()
            svc = services[i % 5]
            trace = f"trace-{10 + i:04d}" if i < 3 else None
            span = f"span-{10 + i:04d}" if i < 3 else None
            self.entries.append(LogEntry(
                f"log-{entry_id:03d}", ts, svc, "WARN", warn_messages[i],
                trace, span, {"component": "middleware"},
            ))

        # 7 ERROR entries
        error_messages = [
            "Failed to process payment: timeout",
            "Database connection refused",
            "Failed to process ride request: validation error",
            "Rate limit exceeded for /api/v1/users",
            "Failed to process notification: template not found",
            "Authentication token expired",
            "Rate limit exceeded for /api/v1/rides",
        ]
        for i in range(7):
            entry_id += 1
            ts = (now - timedelta(minutes=40 - i)).isoformat()
            svc = services[i % 5]
            trace = f"trace-{20 + i:04d}" if i < 3 else None
            span = f"span-{20 + i:04d}" if i < 3 else None
            self.entries.append(LogEntry(
                f"log-{entry_id:03d}", ts, svc, "ERROR", error_messages[i],
                trace, span, {"error_code": f"E{1000 + i}"},
            ))

        # 5 DEBUG entries
        debug_messages = [
            "Parsing request body: 1.2KB",
            "Cache miss for key user:1001",
            "SQL query plan: seq scan on rides",
            "WebSocket ping received",
            "Feature flag 'new-pricing' evaluated: true",
        ]
        for i in range(5):
            entry_id += 1
            ts = (now - timedelta(minutes=30 - i)).isoformat()
            svc = services[i % 5]
            self.entries.append(LogEntry(
                f"log-{entry_id:03d}", ts, svc, "DEBUG", debug_messages[i],
                None, None, {"verbose": True},
            ))

        # Patterns
        self.patterns = [
            LogPattern("pat-001", "Connection timeout to {service}", 8, (now - timedelta(hours=2)).isoformat(), now.isoformat(), "Connection timeout to redis"),
            LogPattern("pat-002", "Failed to process {entity}", 5, (now - timedelta(hours=3)).isoformat(), now.isoformat(), "Failed to process payment: timeout"),
            LogPattern("pat-003", "Rate limit exceeded for {endpoint}", 3, (now - timedelta(hours=1)).isoformat(), now.isoformat(), "Rate limit exceeded for /api/v1/users"),
        ]

        # Retention policies
        self.retention_policies = [
            RetentionPolicy("ret-001", "default", "*", "*", 30, True),
            RetentionPolicy("ret-002", "errors-extended", "*", "ERROR", 90, True),
        ]

    # ── Ingest ──

    def ingest(self, data: dict) -> LogEntry:
        entry_id = f"log-{uuid.uuid4().hex[:8]}"
        ts = datetime.now(timezone.utc).isoformat()
        entry = LogEntry(
            id=entry_id,
            timestamp=ts,
            service_name=data["service_name"],
            level=data["level"],
            message=data["message"],
            trace_id=data.get("trace_id"),
            span_id=data.get("span_id"),
            fields=data.get("fields", {}),
        )
        self.entries.append(entry)
        return entry

    # ── Query ──

    def query(
        self,
        service_name: str | None = None,
        level: str | None = None,
        time_start: str | None = None,
        time_end: str | None = None,
        search: str | None = None,
        limit: int = 100,
    ) -> list[LogEntry]:
        results = list(self.entries)
        if service_name:
            results = [e for e in results if e.service_name == service_name]
        if level:
            results = [e for e in results if e.level == level]
        if time_start:
            results = [e for e in results if e.timestamp >= time_start]
        if time_end:
            results = [e for e in results if e.timestamp <= time_end]
        if search:
            results = [e for e in results if search.lower() in e.message.lower()]
        return results[:limit]

    # ── Patterns ──

    def list_patterns(self) -> list[LogPattern]:
        return list(self.patterns)

    # ── Retention Policies ──

    def list_retention_policies(self) -> list[RetentionPolicy]:
        return list(self.retention_policies)

    def create_retention_policy(self, data: dict) -> RetentionPolicy:
        pol_id = f"ret-{uuid.uuid4().hex[:8]}"
        policy = RetentionPolicy(
            id=pol_id,
            name=data["name"],
            service_filter=data.get("service_filter", "*"),
            level_filter=data.get("level_filter", "*"),
            retention_days=data.get("retention_days", 30),
            is_active=data.get("is_active", True),
        )
        self.retention_policies.append(policy)
        return policy

    # ── Stats ──

    def get_stats(self) -> dict:
        by_level: dict[str, int] = {}
        by_service: dict[str, int] = {}
        entries_with_traces = 0
        for e in self.entries:
            by_level[e.level] = by_level.get(e.level, 0) + 1
            by_service[e.service_name] = by_service.get(e.service_name, 0) + 1
            if e.trace_id:
                entries_with_traces += 1
        return {
            "total_entries": len(self.entries),
            "by_level": by_level,
            "by_service": by_service,
            "entries_with_traces": entries_with_traces,
        }


REPO_CLASS = LogAggregationRepository
repo = LogAggregationRepository(seed=True)
