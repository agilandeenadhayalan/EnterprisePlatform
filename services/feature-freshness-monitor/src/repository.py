"""
In-memory repository for the Feature Freshness Monitor service with pre-seeded data.
"""

from models import FreshnessStatus, FreshnessViolation


class FreshnessMonitorRepository:
    """In-memory store for feature freshness monitoring."""

    def __init__(self, seed: bool = False):
        self.statuses: dict[str, FreshnessStatus] = {}
        self.slas: dict[str, int] = {}
        if seed:
            self._seed()

    def _seed(self):
        # Fresh features (updated recently, within SLA)
        fresh_features = [
            ("driver_avg_rating", "2026-03-09T11:50:00Z", 1800, 600),
            ("driver_total_trips_30d", "2026-03-09T11:45:00Z", 3600, 900),
            ("driver_earnings_per_hour", "2026-03-09T11:30:00Z", 3600, 1800),
            ("driver_acceptance_rate", "2026-03-09T11:55:00Z", 1800, 300),
            ("zone_demand_last_hour", "2026-03-09T11:58:00Z", 300, 120),
            ("zone_avg_fare", "2026-03-09T11:40:00Z", 1800, 1200),
            ("zone_supply_density", "2026-03-09T11:57:00Z", 300, 180),
            ("weather_temperature", "2026-03-09T11:52:00Z", 900, 480),
            ("weather_precipitation", "2026-03-09T11:52:00Z", 900, 480),
            ("weather_wind_speed", "2026-03-09T11:52:00Z", 900, 480),
        ]

        # Stale features (exceeded SLA)
        stale_features = [
            ("driver_cancel_rate", "2026-03-09T08:00:00Z", 1800, 14400),    # 4 hours stale, SLA 30 min
            ("zone_avg_wait_time", "2026-03-09T06:00:00Z", 600, 21600),     # 6 hours stale, SLA 10 min
            ("zone_surge_factor", "2026-03-09T10:00:00Z", 60, 7200),        # 2 hours stale, SLA 1 min
            ("weather_visibility", "2026-03-09T04:00:00Z", 900, 28800),     # 8 hours stale, SLA 15 min
            ("weather_is_severe", "2026-03-09T09:00:00Z", 300, 10800),      # 3 hours stale, SLA 5 min
        ]

        for name, last_updated, sla, staleness in fresh_features:
            self.statuses[name] = FreshnessStatus(
                feature_name=name,
                last_updated=last_updated,
                sla_seconds=sla,
                is_fresh=True,
                staleness_seconds=staleness,
            )
            self.slas[name] = sla

        for name, last_updated, sla, staleness in stale_features:
            self.statuses[name] = FreshnessStatus(
                feature_name=name,
                last_updated=last_updated,
                sla_seconds=sla,
                is_fresh=False,
                staleness_seconds=staleness,
            )
            self.slas[name] = sla

    # ── Dashboard ──

    def get_dashboard(self) -> dict:
        total = len(self.statuses)
        fresh = sum(1 for s in self.statuses.values() if s.is_fresh)
        stale = total - fresh
        violations = self.get_violations()
        critical = sum(1 for v in violations if v.severity == "critical")
        warning = sum(1 for v in violations if v.severity == "warning")
        return {
            "total_features": total,
            "fresh_count": fresh,
            "stale_count": stale,
            "freshness_percentage": round((fresh / total) * 100, 1) if total > 0 else 0.0,
            "critical_violations": critical,
            "warning_violations": warning,
        }

    # ── Feature Status ──

    def get_all_statuses(self) -> list[FreshnessStatus]:
        return list(self.statuses.values())

    # ── Violations ──

    def get_violations(self) -> list[FreshnessViolation]:
        violations = []
        for s in self.statuses.values():
            if not s.is_fresh:
                ratio = s.staleness_seconds / s.sla_seconds
                severity = "critical" if ratio > 5 else "warning"
                violations.append(FreshnessViolation(
                    feature_name=s.feature_name,
                    sla_seconds=s.sla_seconds,
                    actual_staleness=s.staleness_seconds,
                    severity=severity,
                ))
        return violations

    # ── Check Run ──

    def run_check(self) -> dict:
        total = len(self.statuses)
        fresh = sum(1 for s in self.statuses.values() if s.is_fresh)
        stale = total - fresh
        violations = len(self.get_violations())
        return {
            "checked": total,
            "fresh": fresh,
            "stale": stale,
            "violations": violations,
            "message": f"Freshness check completed: {fresh}/{total} features fresh",
        }

    # ── SLA ──

    def set_sla(self, feature_name: str, sla_seconds: int) -> dict:
        self.slas[feature_name] = sla_seconds
        if feature_name in self.statuses:
            status = self.statuses[feature_name]
            status.sla_seconds = sla_seconds
            status.is_fresh = status.staleness_seconds <= sla_seconds
        return {
            "feature_name": feature_name,
            "sla_seconds": sla_seconds,
            "message": f"SLA for '{feature_name}' set to {sla_seconds} seconds",
        }


REPO_CLASS = FreshnessMonitorRepository
repo = FreshnessMonitorRepository(seed=True)
