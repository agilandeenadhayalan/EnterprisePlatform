"""
In-memory SLO tracker repository with pre-seeded data.
"""

import uuid
from datetime import datetime, timezone, timedelta

from models import SloDefinition, SloRecord, BurnRateAlert


def _compute_actual(good: int, total: int) -> float:
    """Compute actual percentage from good/total events."""
    if total == 0:
        return 100.0
    return round(good / total * 100, 4)


def _compute_error_budget_remaining(actual: float, target: float) -> float:
    """Compute error budget remaining percentage."""
    if target >= 100.0:
        return 0.0
    consumed = ((100 - actual) / (100 - target)) * 100
    return round(max(0.0, 100.0 - consumed), 2)


class SloTrackerRepository:
    """In-memory store for SLO definitions, records, and burn rate alerts."""

    def __init__(self, seed: bool = False):
        self.slos: dict[str, SloDefinition] = {}
        self.records: list[SloRecord] = []
        self.alerts: list[BurnRateAlert] = []
        if seed:
            self._seed()

    def _seed(self):
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        slos = [
            SloDefinition("slo-001", "auth-service", "availability", 99.9, 30, "Auth service availability SLO", now_iso),
            SloDefinition("slo-002", "payment-service", "latency", 99.0, 30, "Payment service P99 latency < 200ms", now_iso),
            SloDefinition("slo-003", "ride-service", "error_rate", 99.9, 30, "Ride service error rate < 0.1%", now_iso),
            SloDefinition("slo-004", "api-gateway", "availability", 99.95, 7, "API gateway availability SLO", now_iso),
            SloDefinition("slo-005", "notification-service", "throughput", 99.5, 30, "Notification service throughput SLO", now_iso),
        ]
        for s in slos:
            self.slos[s.id] = s

        # 4 weekly records per SLO (20 total)
        record_configs = [
            # auth-service (99.9% target) — some budget depletion
            ("slo-001", 99.95, 99.92, 99.85, 99.90),
            # payment-service (99.0% target) — good compliance
            ("slo-002", 99.5, 99.3, 99.2, 99.1),
            # ride-service (99.9% target) — some issues
            ("slo-003", 99.95, 99.88, 99.82, 99.91),
            # api-gateway (99.95% target) — tight budget
            ("slo-004", 99.98, 99.96, 99.93, 99.97),
            # notification-service (99.5% target) — good
            ("slo-005", 99.8, 99.7, 99.6, 99.55),
        ]

        rec_idx = 1
        for slo_id, *percentages in record_configs:
            slo = self.slos[slo_id]
            for week_offset, actual_pct in enumerate(percentages):
                start = now - timedelta(days=(4 - week_offset) * 7)
                end = start + timedelta(days=7)
                total_events = 100000
                good_events = int(total_events * actual_pct / 100)
                actual = _compute_actual(good_events, total_events)
                budget = _compute_error_budget_remaining(actual, slo.target_percentage)
                record = SloRecord(
                    id=f"rec-{rec_idx:03d}",
                    slo_id=slo_id,
                    period_start=start.isoformat(),
                    period_end=end.isoformat(),
                    good_events=good_events,
                    total_events=total_events,
                    actual_percentage=actual,
                    error_budget_remaining=budget,
                )
                self.records.append(record)
                rec_idx += 1

        alerts = [
            BurnRateAlert("bra-001", "slo-001", 2.5, 2.0, True, now_iso, "Auth service burn rate exceeds critical threshold"),
            BurnRateAlert("bra-002", "slo-002", 1.8, 1.5, False, now_iso, "Payment service burn rate elevated"),
            BurnRateAlert("bra-003", "slo-003", 3.0, 2.0, True, now_iso, "Ride service burn rate critically high"),
        ]
        self.alerts.extend(alerts)

    # ── SLO Definitions ──

    def list_slos(self) -> list[SloDefinition]:
        return list(self.slos.values())

    def get_slo(self, slo_id: str) -> SloDefinition | None:
        return self.slos.get(slo_id)

    def create_slo(self, data: dict) -> SloDefinition:
        slo_id = f"slo-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()
        slo = SloDefinition(
            id=slo_id,
            service_name=data["service_name"],
            slo_type=data["slo_type"],
            target_percentage=data["target_percentage"],
            window_days=data.get("window_days", 30),
            description=data.get("description", ""),
            created_at=now,
        )
        self.slos[slo.id] = slo
        return slo

    def find_slo_by_service_and_type(self, service_name: str, slo_type: str) -> SloDefinition | None:
        for s in self.slos.values():
            if s.service_name == service_name and s.slo_type == slo_type:
                return s
        return None

    # ── SLO Records ──

    def list_records_for_slo(self, slo_id: str) -> list[SloRecord]:
        records = [r for r in self.records if r.slo_id == slo_id]
        return sorted(records, key=lambda r: r.period_start)

    def record_measurement(self, slo_id: str, good_events: int, total_events: int) -> SloRecord | None:
        slo = self.slos.get(slo_id)
        if not slo:
            return None
        now = datetime.now(timezone.utc)
        actual = _compute_actual(good_events, total_events)
        budget = _compute_error_budget_remaining(actual, slo.target_percentage)
        record = SloRecord(
            id=f"rec-{uuid.uuid4().hex[:8]}",
            slo_id=slo_id,
            period_start=(now - timedelta(days=7)).isoformat(),
            period_end=now.isoformat(),
            good_events=good_events,
            total_events=total_events,
            actual_percentage=actual,
            error_budget_remaining=budget,
        )
        self.records.append(record)
        return record

    # ── Error Budget ──

    def get_error_budget(self, slo_id: str) -> dict | None:
        slo = self.slos.get(slo_id)
        if not slo:
            return None
        records = self.list_records_for_slo(slo_id)
        if not records:
            return {
                "slo_id": slo_id,
                "target": slo.target_percentage,
                "current_percentage": 100.0,
                "error_budget_total": round(100 - slo.target_percentage, 4),
                "error_budget_remaining": round(100 - slo.target_percentage, 4),
                "error_budget_consumed_percent": 0.0,
                "burn_rate": 0.0,
                "is_budget_exhausted": False,
            }
        latest = records[-1]
        error_budget_total = round(100 - slo.target_percentage, 4)
        actual_error = round(100 - latest.actual_percentage, 4)
        consumed_pct = round((actual_error / error_budget_total) * 100, 2) if error_budget_total > 0 else 0.0
        remaining = round(max(0.0, error_budget_total - actual_error), 4)
        burn_rate = round(actual_error / error_budget_total, 2) if error_budget_total > 0 else 0.0
        return {
            "slo_id": slo_id,
            "target": slo.target_percentage,
            "current_percentage": latest.actual_percentage,
            "error_budget_total": error_budget_total,
            "error_budget_remaining": remaining,
            "error_budget_consumed_percent": consumed_pct,
            "burn_rate": burn_rate,
            "is_budget_exhausted": remaining <= 0,
        }

    # ── Burn Rate Alerts ──

    def list_burn_rate_alerts(self, slo_id: str) -> list[BurnRateAlert]:
        return [a for a in self.alerts if a.slo_id == slo_id]

    # ── Stats ──

    def get_stats(self) -> dict:
        total = len(self.slos)
        by_type: dict[str, int] = {}
        meeting_target = 0
        at_risk = 0
        budget_sum = 0.0
        budget_count = 0
        for slo in self.slos.values():
            by_type[slo.slo_type] = by_type.get(slo.slo_type, 0) + 1
            budget = self.get_error_budget(slo.id)
            if budget:
                budget_count += 1
                budget_sum += budget["error_budget_remaining"]
                if budget["current_percentage"] >= slo.target_percentage:
                    meeting_target += 1
                if budget["error_budget_remaining"] < (100 - slo.target_percentage) * 0.20:
                    at_risk += 1
        avg_budget = round(budget_sum / budget_count, 2) if budget_count > 0 else 0.0
        return {
            "total_slos": total,
            "slos_meeting_target": meeting_target,
            "slos_at_risk": at_risk,
            "avg_error_budget_remaining": avg_budget,
            "by_type": by_type,
        }


REPO_CLASS = SloTrackerRepository
repo = SloTrackerRepository(seed=True)
