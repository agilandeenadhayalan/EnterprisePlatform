"""
Domain models for the Feature Freshness Monitor service.
"""


class FreshnessStatus:
    """Freshness status for a single feature."""

    def __init__(
        self,
        feature_name: str,
        last_updated: str,
        sla_seconds: int,
        is_fresh: bool,
        staleness_seconds: float,
    ):
        self.feature_name = feature_name
        self.last_updated = last_updated
        self.sla_seconds = sla_seconds
        self.is_fresh = is_fresh
        self.staleness_seconds = staleness_seconds

    def to_dict(self) -> dict:
        return {
            "feature_name": self.feature_name,
            "last_updated": self.last_updated,
            "sla_seconds": self.sla_seconds,
            "is_fresh": self.is_fresh,
            "staleness_seconds": self.staleness_seconds,
        }


class FreshnessViolation:
    """A freshness SLA violation record."""

    def __init__(
        self,
        feature_name: str,
        sla_seconds: int,
        actual_staleness: float,
        severity: str,
    ):
        self.feature_name = feature_name
        self.sla_seconds = sla_seconds
        self.actual_staleness = actual_staleness
        self.severity = severity

    def to_dict(self) -> dict:
        return {
            "feature_name": self.feature_name,
            "sla_seconds": self.sla_seconds,
            "actual_staleness": self.actual_staleness,
            "severity": self.severity,
        }
