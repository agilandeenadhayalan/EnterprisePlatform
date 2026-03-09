"""
In-memory synthetic monitor repository with pre-seeded data.
"""

import uuid
import random
from datetime import datetime, timezone, timedelta

from models import SyntheticMonitor, SyntheticResult, UptimeReport


class SyntheticMonitorRepository:
    """In-memory store for synthetic monitors, results, and uptime reports."""

    def __init__(self, seed: bool = False):
        self.monitors: dict[str, SyntheticMonitor] = {}
        self.results: list[SyntheticResult] = []
        self.uptime_reports: dict[str, UptimeReport] = {}
        if seed:
            self._seed()

    def _seed(self):
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        monitors = [
            SyntheticMonitor("mon-001", "API Gateway Health", "http", "http://api-gateway:8080/health", 30, 30, 200, True, now_iso),
            SyntheticMonitor("mon-002", "Auth Service Health", "http", "http://auth-service:8000/health", 60, 30, 200, True, now_iso),
            SyntheticMonitor("mon-003", "DNS Resolution", "dns", "api.mobility.local", 300, 10, 200, True, now_iso),
            SyntheticMonitor("mon-004", "Postgres Port", "tcp", "postgres:5432", 60, 5, 200, True, now_iso),
            SyntheticMonitor("mon-005", "Payment Webhook", "http", "http://payment-service:8000/webhook", 120, 30, 200, False, now_iso),
        ]
        for m in monitors:
            self.monitors[m.id] = m

        # 30 results: 25 successful, 5 failed
        # API Gateway gets most checks (10), others get 5 each
        result_idx = 1
        random.seed(42)  # Deterministic seed for reproducibility

        # API Gateway — 10 checks: 8 success, 2 fail
        for i in range(10):
            checked = now - timedelta(minutes=(10 - i) * 5)
            is_success = i not in (3, 7)  # 2 failures
            status_code = 200 if is_success else 500
            response_time = round(random.uniform(10, 200), 2) if is_success else round(random.uniform(500, 2000), 2)
            error_msg = None if is_success else "Internal server error"
            self.results.append(SyntheticResult(
                f"res-{result_idx:03d}", "mon-001", "API Gateway Health",
                status_code, response_time, is_success, error_msg, checked.isoformat(),
            ))
            result_idx += 1

        # Auth Service — 5 checks: 4 success, 1 fail
        for i in range(5):
            checked = now - timedelta(minutes=(5 - i) * 10)
            is_success = i != 2
            status_code = 200 if is_success else 500
            response_time = round(random.uniform(15, 150), 2) if is_success else round(random.uniform(600, 1500), 2)
            error_msg = None if is_success else "Service unavailable"
            self.results.append(SyntheticResult(
                f"res-{result_idx:03d}", "mon-002", "Auth Service Health",
                status_code, response_time, is_success, error_msg, checked.isoformat(),
            ))
            result_idx += 1

        # DNS — 5 checks: all success
        for i in range(5):
            checked = now - timedelta(minutes=(5 - i) * 15)
            response_time = round(random.uniform(5, 50), 2)
            self.results.append(SyntheticResult(
                f"res-{result_idx:03d}", "mon-003", "DNS Resolution",
                200, response_time, True, None, checked.isoformat(),
            ))
            result_idx += 1

        # Postgres — 5 checks: 4 success, 1 fail
        for i in range(5):
            checked = now - timedelta(minutes=(5 - i) * 10)
            is_success = i != 4
            status_code = 200 if is_success else 0
            response_time = round(random.uniform(1, 15), 2) if is_success else round(random.uniform(5000, 6000), 2)
            error_msg = None if is_success else "Connection timeout"
            self.results.append(SyntheticResult(
                f"res-{result_idx:03d}", "mon-004", "Postgres Port",
                status_code, response_time, is_success, error_msg, checked.isoformat(),
            ))
            result_idx += 1

        # Payment Webhook — 5 checks: 4 success, 1 fail
        for i in range(5):
            checked = now - timedelta(minutes=(5 - i) * 20)
            is_success = i != 1
            status_code = 200 if is_success else 502
            response_time = round(random.uniform(20, 180), 2) if is_success else round(random.uniform(800, 2000), 2)
            error_msg = None if is_success else "Bad gateway"
            self.results.append(SyntheticResult(
                f"res-{result_idx:03d}", "mon-005", "Payment Webhook",
                status_code, response_time, is_success, error_msg, checked.isoformat(),
            ))
            result_idx += 1

        # Pre-compute uptime reports
        for mon_id, mon in self.monitors.items():
            report = self._compute_uptime_report(mon_id)
            if report:
                self.uptime_reports[mon_id] = report

    def _compute_uptime_report(self, monitor_id: str) -> UptimeReport | None:
        mon = self.monitors.get(monitor_id)
        if not mon:
            return None
        results = [r for r in self.results if r.monitor_id == monitor_id]
        if not results:
            return UptimeReport(monitor_id, mon.name, 24, 0, 0, 100.0, 0.0, 0.0, 0.0)
        total = len(results)
        successful = sum(1 for r in results if r.is_success)
        uptime = round(successful / total * 100, 2)
        times = [r.response_time_ms for r in results]
        avg_time = round(sum(times) / len(times), 2)
        sorted_times = sorted(times)
        p95_idx = min(int(len(sorted_times) * 0.95), len(sorted_times) - 1)
        p99_idx = min(int(len(sorted_times) * 0.99), len(sorted_times) - 1)
        return UptimeReport(
            monitor_id=monitor_id,
            monitor_name=mon.name,
            period_hours=24,
            total_checks=total,
            successful_checks=successful,
            uptime_percentage=uptime,
            avg_response_time_ms=avg_time,
            p95_response_time_ms=sorted_times[p95_idx],
            p99_response_time_ms=sorted_times[p99_idx],
        )

    # ── Monitors ──

    def list_monitors(self) -> list[SyntheticMonitor]:
        return list(self.monitors.values())

    def get_monitor(self, mon_id: str) -> SyntheticMonitor | None:
        return self.monitors.get(mon_id)

    def create_monitor(self, data: dict) -> SyntheticMonitor:
        mon_id = f"mon-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()
        mon = SyntheticMonitor(
            id=mon_id,
            name=data["name"],
            monitor_type=data["monitor_type"],
            target_url=data["target_url"],
            interval_seconds=data.get("interval_seconds", 60),
            timeout_seconds=data.get("timeout_seconds", 30),
            expected_status_code=data.get("expected_status_code", 200),
            is_active=data.get("is_active", True),
            created_at=now,
        )
        self.monitors[mon.id] = mon
        return mon

    # ── Run Check ──

    def run_check(self, mon_id: str) -> SyntheticResult | None:
        mon = self.monitors.get(mon_id)
        if not mon:
            return None
        now = datetime.now(timezone.utc).isoformat()

        # Simulate check based on monitor type
        if mon.monitor_type == "http":
            response_time = round(random.uniform(10, 200), 2)
            status_code = 200
        elif mon.monitor_type == "dns":
            response_time = round(random.uniform(5, 50), 2)
            status_code = 200
        elif mon.monitor_type == "tcp":
            response_time = round(random.uniform(1, 15), 2)
            status_code = 200
        else:
            response_time = round(random.uniform(10, 200), 2)
            status_code = 200

        is_success = response_time <= mon.timeout_seconds * 1000
        error_msg = None
        if not is_success:
            status_code = 0
            error_msg = "Request timeout"

        result = SyntheticResult(
            id=f"res-{uuid.uuid4().hex[:8]}",
            monitor_id=mon.id,
            monitor_name=mon.name,
            status_code=status_code,
            response_time_ms=response_time,
            is_success=is_success,
            error_message=error_msg,
            checked_at=now,
        )
        self.results.append(result)
        return result

    # ── Results ──

    def list_results(self) -> list[SyntheticResult]:
        return list(self.results)

    def list_results_for_monitor(self, mon_id: str) -> list[SyntheticResult]:
        return [r for r in self.results if r.monitor_id == mon_id]

    # ── Uptime ──

    def get_uptime_report(self, mon_id: str) -> UptimeReport | None:
        return self._compute_uptime_report(mon_id)

    # ── Stats ──

    def get_stats(self) -> dict:
        total = len(self.monitors)
        active = sum(1 for m in self.monitors.values() if m.is_active)
        total_checks = len(self.results)
        successful = sum(1 for r in self.results if r.is_success)
        overall_uptime = round(successful / total_checks * 100, 2) if total_checks > 0 else 100.0
        times = [r.response_time_ms for r in self.results]
        avg_time = round(sum(times) / len(times), 2) if times else 0.0
        return {
            "total_monitors": total,
            "active_monitors": active,
            "total_checks": total_checks,
            "overall_uptime_percentage": overall_uptime,
            "avg_response_time_ms": avg_time,
        }


REPO_CLASS = SyntheticMonitorRepository
repo = SyntheticMonitorRepository(seed=True)
