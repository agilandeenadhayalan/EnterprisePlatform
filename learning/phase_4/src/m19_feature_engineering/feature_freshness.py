"""
Feature Freshness Monitoring
=============================

In production ML systems, features go stale when the pipelines that compute
them fail or slow down. Stale features cause silent model degradation -- the
model keeps making predictions, but they're based on outdated information.

For example:
- A "zone demand" feature should update every 5 minutes. If the pipeline
  computing it breaks, the model keeps using 3-hour-old demand data,
  leading to poor surge pricing decisions.

- A "driver rating" feature might have a 1-hour SLA. If it's 2 hours stale,
  the model might assign rides to drivers whose ratings have dropped.

FreshnessChecker monitors each feature's age against its SLA and reports
violations so operators can detect and fix pipeline failures before they
impact model quality.
"""

from __future__ import annotations


class FreshnessChecker:
    """Monitors feature freshness against SLA targets.

    Usage:
        checker = FreshnessChecker()
        checker.register_sla("zone_demand", max_staleness_seconds=300)
        checker.update_timestamp("zone_demand", time.time())

        # Later...
        result = checker.check_freshness("zone_demand", time.time())
        # -> {"feature": "zone_demand", "fresh": True, "age_seconds": 120, ...}
    """

    def __init__(self) -> None:
        self._slas: dict[str, float] = {}
        self._timestamps: dict[str, float] = {}

    def register_sla(self, feature_name: str, max_staleness_seconds: float) -> None:
        """Register a freshness SLA for a feature.

        Args:
            feature_name: Name of the feature to monitor.
            max_staleness_seconds: Maximum acceptable age in seconds.

        Raises:
            ValueError: If max_staleness_seconds is not positive.
        """
        if max_staleness_seconds <= 0:
            raise ValueError("max_staleness_seconds must be positive")
        self._slas[feature_name] = max_staleness_seconds

    def update_timestamp(self, feature_name: str, timestamp: float) -> None:
        """Record when a feature was last computed/updated.

        Args:
            feature_name: Name of the feature.
            timestamp: Unix timestamp of when the feature was last updated.

        Raises:
            KeyError: If no SLA is registered for this feature.
        """
        if feature_name not in self._slas:
            raise KeyError(
                f"No SLA registered for feature {feature_name!r}. "
                f"Call register_sla() first."
            )
        self._timestamps[feature_name] = timestamp

    def check_freshness(self, feature_name: str, current_time: float) -> dict:
        """Check whether a single feature meets its freshness SLA.

        Args:
            feature_name: Name of the feature to check.
            current_time: Current unix timestamp.

        Returns:
            Dict with keys:
            - feature: the feature name
            - fresh: True if within SLA
            - age_seconds: seconds since last update (or None if never updated)
            - max_staleness_seconds: the SLA threshold
            - status: 'fresh', 'stale', or 'unknown' (never updated)

        Raises:
            KeyError: If no SLA is registered for this feature.
        """
        if feature_name not in self._slas:
            raise KeyError(f"No SLA registered for feature {feature_name!r}")

        max_staleness = self._slas[feature_name]
        last_updated = self._timestamps.get(feature_name)

        if last_updated is None:
            return {
                "feature": feature_name,
                "fresh": False,
                "age_seconds": None,
                "max_staleness_seconds": max_staleness,
                "status": "unknown",
            }

        age = current_time - last_updated
        is_fresh = age <= max_staleness

        return {
            "feature": feature_name,
            "fresh": is_fresh,
            "age_seconds": age,
            "max_staleness_seconds": max_staleness,
            "status": "fresh" if is_fresh else "stale",
        }

    def check_all(self, current_time: float) -> list[dict]:
        """Check freshness of all registered features.

        Returns:
            List of freshness check results, one per registered feature,
            sorted by feature name.
        """
        results = []
        for feature_name in sorted(self._slas.keys()):
            results.append(self.check_freshness(feature_name, current_time))
        return results

    def get_violations(self, current_time: float) -> list[dict]:
        """Return only features that are violating their SLA.

        This is what an alerting system would call periodically.

        Returns:
            List of freshness check results where status is 'stale' or 'unknown',
            sorted by feature name.
        """
        all_results = self.check_all(current_time)
        return [r for r in all_results if not r["fresh"]]
