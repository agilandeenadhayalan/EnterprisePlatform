"""
Demo: Data Quality Framework Concepts
========================================

Runs demonstrations of data profiling, quality rules, and anomaly detection.
"""

from m17_data_quality.profiling import (
    DataProfiler,
    DistributionAnalysis,
    CardinalityEstimation,
)
from m17_data_quality.rule_engine import (
    RuleEngine,
    QualityRule,
    RuleType,
    Severity,
)
from m17_data_quality.anomaly_detection import (
    ZScoreDetector,
    IQRDetector,
    MovingAverageDetector,
)


def demo_profiling() -> None:
    print("=" * 60)
    print("DATA PROFILING")
    print("=" * 60)

    data = [
        {"ride_id": "r1", "zone": "Manhattan", "fare": 25.0, "distance": 5.2},
        {"ride_id": "r2", "zone": "Brooklyn", "fare": 18.0, "distance": 3.5},
        {"ride_id": "r3", "zone": "Manhattan", "fare": 35.0, "distance": 8.1},
        {"ride_id": "r4", "zone": "Queens", "fare": None, "distance": 4.0},
        {"ride_id": "r5", "zone": "Manhattan", "fare": 42.0, "distance": 10.5},
    ]

    profiler = DataProfiler(data)
    print(f"\nDataset: {profiler.row_count} rows, {len(profiler.columns)} columns")
    for profile in profiler.profile_all():
        print(f"\n  {profile.column_name} ({profile.dtype}):")
        print(f"    Count: {profile.count}, Nulls: {profile.null_count} ({profile.null_pct}%)")
        print(f"    Distinct: {profile.distinct_count}")
        if profile.mean is not None:
            print(f"    Min: {profile.min_value}, Max: {profile.max_value}")
            print(f"    Mean: {profile.mean}, Median: {profile.median}, StdDev: {profile.std_dev}")

    # Distribution analysis
    fares = [25.0, 18.0, 35.0, 42.0, 15.0, 28.0, 55.0, 22.0]
    pcts = DistributionAnalysis.percentiles(fares)
    print(f"\nFare Percentiles: {pcts}")
    print(f"Skewness: {DistributionAnalysis.skewness(fares)}")


def demo_quality_rules() -> None:
    print("\n" + "=" * 60)
    print("DATA QUALITY RULES")
    print("=" * 60)

    data = [
        {"ride_id": "r1", "zone": "Manhattan", "fare": 25.0, "status": "completed"},
        {"ride_id": "r2", "zone": "Brooklyn", "fare": 18.0, "status": "completed"},
        {"ride_id": "r3", "zone": "Manhattan", "fare": None, "status": "completed"},
        {"ride_id": "r1", "zone": "Queens", "fare": 600.0, "status": "cancelled"},
    ]

    engine = RuleEngine()
    engine.add_rule(QualityRule(
        name="fare_completeness", rule_type=RuleType.COMPLETENESS,
        column="fare", threshold=90.0, severity=Severity.CRITICAL,
    ))
    engine.add_rule(QualityRule(
        name="fare_accuracy", rule_type=RuleType.ACCURACY,
        column="fare", threshold=90.0, min_value=1.0, max_value=500.0,
        severity=Severity.WARNING,
    ))
    engine.add_rule(QualityRule(
        name="ride_id_unique", rule_type=RuleType.UNIQUENESS,
        column="ride_id", threshold=100.0, severity=Severity.CRITICAL,
    ))

    results = engine.evaluate(data)
    for result in results:
        icon = "PASS" if result.status.value == "pass" else "FAIL"
        print(f"\n  [{icon}] {result.rule_name} ({result.severity.value})")
        print(f"    Metric: {result.metric_value}% (threshold: {result.threshold}%)")
        print(f"    {result.details}")


def demo_anomaly_detection() -> None:
    print("\n" + "=" * 60)
    print("ANOMALY DETECTION")
    print("=" * 60)

    # Normal fares with outliers
    fares = [25, 28, 22, 30, 27, 24, 26, 29, 23, 150, 25, 27, 24, -5]

    # Z-Score
    print("\n--- Z-Score Detection ---")
    z_report = ZScoreDetector(threshold=2.0).detect(fares)
    print(f"  Found {z_report.anomaly_count} anomalies ({z_report.anomaly_rate}%)")
    for a in z_report.anomalies:
        print(f"    Index {a.index}: value={a.value}, z-score={a.deviation}, severity={a.severity}")

    # IQR
    print("\n--- IQR Detection ---")
    iqr_report = IQRDetector(multiplier=1.5).detect(fares)
    print(f"  Found {iqr_report.anomaly_count} anomalies ({iqr_report.anomaly_rate}%)")
    for a in iqr_report.anomalies:
        print(f"    Index {a.index}: value={a.value}, severity={a.severity}")

    # Moving Average
    print("\n--- Moving Average Detection ---")
    time_series = [10, 11, 10, 12, 11, 50, 10, 11, 12, 10]
    ma_report = MovingAverageDetector(window_size=4, threshold=2.0).detect(time_series)
    print(f"  Found {ma_report.anomaly_count} anomalies in time series")
    for a in ma_report.anomalies:
        print(f"    Index {a.index}: value={a.value}, expected={a.expected}")


if __name__ == "__main__":
    demo_profiling()
    demo_quality_rules()
    demo_anomaly_detection()
