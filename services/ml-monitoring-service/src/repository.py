"""
In-memory ML monitoring repository with pre-seeded data.
"""

import math
from models import DriftResult, ReferenceDistribution, DriftAlert, ConceptDriftResult


def _compute_psi(reference: list[float], current: list[float], num_bins: int = 10) -> float:
    """Compute Population Stability Index between two distributions."""
    all_vals = reference + current
    if not all_vals:
        return 0.0
    min_val = min(all_vals)
    max_val = max(all_vals)
    if min_val == max_val:
        return 0.0
    bin_width = (max_val - min_val) / num_bins
    eps = 1e-4

    def _bin_counts(data):
        counts = [0] * num_bins
        for v in data:
            idx = min(int((v - min_val) / bin_width), num_bins - 1)
            counts[idx] += 1
        return [c / len(data) if len(data) > 0 else eps for c in counts]

    ref_pcts = _bin_counts(reference)
    cur_pcts = _bin_counts(current)

    psi = 0.0
    for r, c in zip(ref_pcts, cur_pcts):
        r = max(r, eps)
        c = max(c, eps)
        psi += (c - r) * math.log(c / r)
    return round(psi, 6)


def _compute_ks(reference: list[float], current: list[float]) -> float:
    """Compute Kolmogorov-Smirnov statistic between two distributions."""
    if not reference or not current:
        return 0.0
    ref_sorted = sorted(reference)
    cur_sorted = sorted(current)
    all_vals = sorted(set(ref_sorted + cur_sorted))

    max_diff = 0.0
    for v in all_vals:
        ref_cdf = sum(1 for x in ref_sorted if x <= v) / len(ref_sorted)
        cur_cdf = sum(1 for x in cur_sorted if x <= v) / len(cur_sorted)
        diff = abs(ref_cdf - cur_cdf)
        if diff > max_diff:
            max_diff = diff
    return round(max_diff, 6)


def _compute_jsd(reference: list[float], current: list[float], num_bins: int = 10) -> float:
    """Compute Jensen-Shannon Divergence between two distributions."""
    all_vals = reference + current
    if not all_vals:
        return 0.0
    min_val = min(all_vals)
    max_val = max(all_vals)
    if min_val == max_val:
        return 0.0
    bin_width = (max_val - min_val) / num_bins
    eps = 1e-10

    def _bin_probs(data):
        counts = [0] * num_bins
        for v in data:
            idx = min(int((v - min_val) / bin_width), num_bins - 1)
            counts[idx] += 1
        total = sum(counts)
        return [c / total if total > 0 else eps for c in counts]

    p = _bin_probs(reference)
    q = _bin_probs(current)

    m = [(pi + qi) / 2 for pi, qi in zip(p, q)]

    def _kl(a, b):
        return sum(ai * math.log(ai / bi) for ai, bi in zip(a, b) if ai > eps and bi > eps)

    jsd = 0.5 * _kl(p, m) + 0.5 * _kl(q, m)
    return round(jsd, 6)


class MLMonitoringRepository:
    """In-memory store for drift results, reference distributions, and alerts."""

    PSI_THRESHOLD = 0.2
    KS_THRESHOLD = 0.15
    JSD_THRESHOLD = 0.1

    def __init__(self, seed: bool = False):
        self.drift_results: list[DriftResult] = []
        self.references: dict[str, ReferenceDistribution] = {}
        self.alerts: list[DriftAlert] = []
        if seed:
            self._seed()

    def _seed(self):
        # Reference distributions for 5 features
        import random
        rng = random.Random(42)
        feature_seeds = {
            "trip_distance": [rng.gauss(5.0, 2.0) for _ in range(100)],
            "fare_amount": [rng.gauss(15.0, 5.0) for _ in range(100)],
            "driver_rating": [rng.gauss(4.5, 0.3) for _ in range(100)],
            "wait_time": [rng.gauss(300, 60) for _ in range(100)],
            "surge_multiplier": [rng.gauss(1.2, 0.3) for _ in range(100)],
        }
        for name, vals in feature_seeds.items():
            self.references[name] = ReferenceDistribution(
                feature_name=name, values=vals, set_at="2026-03-01T00:00:00Z",
            )

        # 8 drift results: some drifted, some not
        self.drift_results = [
            DriftResult("trip_distance", "data", "psi", 0.05, 0.2, False, id="dr-001", detected_at="2026-03-08T10:00:00Z"),
            DriftResult("trip_distance", "data", "ks", 0.08, 0.15, False, id="dr-002", detected_at="2026-03-08T10:00:00Z"),
            DriftResult("fare_amount", "data", "psi", 0.35, 0.2, True, id="dr-003", detected_at="2026-03-08T14:00:00Z"),
            DriftResult("fare_amount", "data", "jsd", 0.18, 0.1, True, id="dr-004", detected_at="2026-03-08T14:00:00Z"),
            DriftResult("driver_rating", "data", "psi", 0.12, 0.2, False, id="dr-005", detected_at="2026-03-09T08:00:00Z"),
            DriftResult("wait_time", "data", "ks", 0.22, 0.15, True, id="dr-006", detected_at="2026-03-09T09:00:00Z"),
            DriftResult("surge_multiplier", "data", "psi", 0.03, 0.2, False, id="dr-007", detected_at="2026-03-09T10:00:00Z"),
            DriftResult("surge_multiplier", "data", "jsd", 0.02, 0.1, False, id="dr-008", detected_at="2026-03-09T10:00:00Z"),
        ]

        # 3 alerts for drifted features
        self.alerts = [
            DriftAlert("fare_amount", "data", "high", "PSI=0.35 exceeds threshold 0.2", id="alert-001", created_at="2026-03-08T14:01:00Z"),
            DriftAlert("fare_amount", "data", "high", "JSD=0.18 exceeds threshold 0.1", id="alert-002", created_at="2026-03-08T14:01:00Z"),
            DriftAlert("wait_time", "data", "medium", "KS=0.22 exceeds threshold 0.15", id="alert-003", created_at="2026-03-09T09:01:00Z"),
        ]

    # ── Drift detection ──

    def detect_drift(self, feature_name: str, reference_data: list[float],
                     current_data: list[float], method: str) -> DriftResult:
        method = method.lower()
        if method == "psi":
            value = _compute_psi(reference_data, current_data)
            threshold = self.PSI_THRESHOLD
        elif method == "ks":
            value = _compute_ks(reference_data, current_data)
            threshold = self.KS_THRESHOLD
        elif method == "jsd":
            value = _compute_jsd(reference_data, current_data)
            threshold = self.JSD_THRESHOLD
        else:
            value = _compute_psi(reference_data, current_data)
            threshold = self.PSI_THRESHOLD

        is_drifted = value > threshold
        result = DriftResult(
            feature_name=feature_name,
            drift_type="data",
            metric_name=method,
            metric_value=value,
            threshold=threshold,
            is_drifted=is_drifted,
        )
        self.drift_results.append(result)

        if is_drifted:
            severity = "high" if value > threshold * 2 else "medium"
            alert = DriftAlert(
                feature_name=feature_name,
                drift_type="data",
                severity=severity,
                message=f"{method.upper()}={value} exceeds threshold {threshold}",
            )
            self.alerts.append(alert)

        return result

    def list_drift_results(self) -> list[DriftResult]:
        return list(self.drift_results)

    # ── Reference distributions ──

    def set_reference(self, feature_name: str, values: list[float]) -> ReferenceDistribution:
        ref = ReferenceDistribution(feature_name=feature_name, values=values)
        self.references[feature_name] = ref
        return ref

    def get_reference(self, feature_name: str) -> ReferenceDistribution | None:
        return self.references.get(feature_name)

    # ── Dashboard ──

    def get_dashboard(self) -> dict:
        all_features = set()
        for r in self.drift_results:
            all_features.add(r.feature_name)
        for name in self.references:
            all_features.add(name)

        features = []
        drifted_count = 0
        for fname in sorted(all_features):
            feature_results = [r for r in self.drift_results if r.feature_name == fname]
            latest = feature_results[-1] if feature_results else None
            has_ref = fname in self.references
            alert_count = sum(1 for a in self.alerts if a.feature_name == fname)
            if latest and latest.is_drifted:
                drifted_count += 1
            features.append({
                "feature_name": fname,
                "latest_result": latest,
                "has_reference": has_ref,
                "alert_count": alert_count,
            })

        return {
            "features": features,
            "total_features": len(features),
            "drifted_count": drifted_count,
        }

    # ── Concept drift ──

    def detect_concept_drift(self, model_name: str, predictions: list[float],
                             actuals: list[float]) -> ConceptDriftResult:
        errors = [abs(p - a) for p, a in zip(predictions, actuals)]
        error_mean = sum(errors) / len(errors) if errors else 0.0

        # Compute trend: compare first half to second half
        if len(errors) >= 4:
            mid = len(errors) // 2
            first_half_mean = sum(errors[:mid]) / mid
            second_half_mean = sum(errors[mid:]) / (len(errors) - mid)
            error_trend = second_half_mean - first_half_mean
        else:
            error_trend = 0.0

        is_drifted = error_trend > 0.1 * error_mean if error_mean > 0 else False

        return ConceptDriftResult(
            model_name=model_name,
            error_mean=round(error_mean, 6),
            error_trend=round(error_trend, 6),
            is_drifted=is_drifted,
        )

    # ── Alerts ──

    def list_alerts(self) -> list[DriftAlert]:
        return list(self.alerts)


REPO_CLASS = MLMonitoringRepository
repo = MLMonitoringRepository(seed=True)
