"""
Tests for Module 19: Feature Engineering.
~30 tests covering feature_types, point_in_time_join, feature_transforms,
and feature_freshness.
"""

import math
import pytest

from m19_feature_engineering.feature_types import (
    Entity,
    OnlineFeature,
    OfflineFeature,
    FeatureGroup,
)
from m19_feature_engineering.point_in_time_join import (
    PointInTimeJoiner,
    NaiveJoiner,
)
from m19_feature_engineering.feature_transforms import (
    BucketTransform,
    LogTransform,
    InteractionFeature,
    WindowAggregate,
)
from m19_feature_engineering.feature_freshness import FreshnessChecker


# ===== Entity Tests =====

class TestEntity:

    def test_create_entity(self):
        e = Entity("driver", "d123")
        assert e.entity_type == "driver"
        assert e.entity_id == "d123"

    def test_entity_equality(self):
        e1 = Entity("driver", "d1")
        e2 = Entity("driver", "d1")
        e3 = Entity("rider", "d1")
        assert e1 == e2
        assert e1 != e3

    def test_entity_hash(self):
        e1 = Entity("driver", "d1")
        e2 = Entity("driver", "d1")
        assert hash(e1) == hash(e2)
        assert {e1, e2} == {e1}

    def test_entity_empty_type_raises(self):
        with pytest.raises(ValueError):
            Entity("", "d1")

    def test_entity_empty_id_raises(self):
        with pytest.raises(ValueError):
            Entity("driver", "")


# ===== OnlineFeature Tests =====

class TestOnlineFeature:

    def test_create_online_feature(self):
        f = OnlineFeature(
            "avg_speed_1h", "driver", "float",
            "Average speed over last hour", 300.0,
        )
        assert f.name == "avg_speed_1h"
        assert f.freshness_sla_seconds == 300.0

    def test_is_fresh_within_sla(self):
        f = OnlineFeature("speed", "driver", "float", "desc", 300.0)
        assert f.is_fresh(last_updated_at=1000.0, current_time=1200.0)

    def test_is_stale_beyond_sla(self):
        f = OnlineFeature("speed", "driver", "float", "desc", 300.0)
        assert not f.is_fresh(last_updated_at=1000.0, current_time=1400.0)

    def test_invalid_value_type_raises(self):
        with pytest.raises(ValueError):
            OnlineFeature("x", "driver", "boolean", "desc", 60.0)

    def test_negative_sla_raises(self):
        with pytest.raises(ValueError):
            OnlineFeature("x", "driver", "float", "desc", -1.0)


# ===== OfflineFeature Tests =====

class TestOfflineFeature:

    def test_create_offline_feature(self):
        f = OfflineFeature(
            "lifetime_trips", "driver", "int",
            "Total trips ever", "SELECT COUNT(*) FROM trips",
        )
        assert f.name == "lifetime_trips"
        assert f.computation_query == "SELECT COUNT(*) FROM trips"


# ===== FeatureGroup Tests =====

class TestFeatureGroup:

    def test_add_and_list_features(self):
        group = FeatureGroup("driver_stats", "driver")
        f1 = OnlineFeature("speed", "driver", "float", "desc", 60.0)
        f2 = OfflineFeature("trips", "driver", "int", "desc", "SELECT ...")
        group.add_feature(f1)
        group.add_feature(f2)
        assert group.list_features() == ["speed", "trips"]
        assert len(group) == 2

    def test_get_feature(self):
        group = FeatureGroup("stats", "driver")
        f = OnlineFeature("speed", "driver", "float", "desc", 60.0)
        group.add_feature(f)
        assert group.get_feature("speed") is f

    def test_get_missing_feature_raises(self):
        group = FeatureGroup("stats", "driver")
        with pytest.raises(KeyError):
            group.get_feature("nonexistent")

    def test_duplicate_name_raises(self):
        group = FeatureGroup("stats", "driver")
        f1 = OnlineFeature("speed", "driver", "float", "desc", 60.0)
        f2 = OnlineFeature("speed", "driver", "float", "desc2", 120.0)
        group.add_feature(f1)
        with pytest.raises(ValueError, match="Duplicate"):
            group.add_feature(f2)

    def test_mismatched_entity_type_raises(self):
        group = FeatureGroup("stats", "driver")
        f = OnlineFeature("demand", "zone", "float", "desc", 60.0)
        with pytest.raises(ValueError, match="entity_type"):
            group.add_feature(f)

    def test_validate_returns_empty_when_valid(self):
        group = FeatureGroup("stats", "driver")
        f = OnlineFeature("speed", "driver", "float", "desc", 60.0)
        group.add_feature(f)
        assert group.validate() == []


# ===== PointInTimeJoiner Tests =====

class TestPointInTimeJoiner:

    def _make_test_data(self):
        labels = [
            {"driver_id": "d1", "ts": 1000.0, "label": 25.0},
            {"driver_id": "d1", "ts": 2000.0, "label": 30.0},
            {"driver_id": "d2", "ts": 1500.0, "label": 15.0},
        ]
        features = [
            {"driver_id": "d1", "ts": 500.0, "speed": 30.0},
            {"driver_id": "d1", "ts": 900.0, "speed": 35.0},
            {"driver_id": "d1", "ts": 1500.0, "speed": 20.0},
            {"driver_id": "d2", "ts": 1400.0, "speed": 45.0},
        ]
        return labels, features

    def test_point_in_time_correctness(self):
        labels, features = self._make_test_data()
        joiner = PointInTimeJoiner(lookback_hours=24)
        results = joiner.join(labels, features, "driver_id", "ts", ["speed"])

        # Label at t=1000 should match feature at t=900 (not 1500!)
        assert results[0]["speed"] == 35.0
        assert results[0]["feature_time"] == 900.0

    def test_future_feature_not_used(self):
        labels, features = self._make_test_data()
        joiner = PointInTimeJoiner(lookback_hours=24)
        results = joiner.join(labels, features, "driver_id", "ts", ["speed"])

        # The feature at t=1500 is AFTER label at t=1000 -- must not be used
        assert results[0]["feature_time"] == 900.0

    def test_lookback_window(self):
        labels = [{"driver_id": "d1", "ts": 10000.0, "label": 1.0}]
        features = [{"driver_id": "d1", "ts": 1.0, "speed": 99.0}]
        joiner = PointInTimeJoiner(lookback_hours=1)
        results = joiner.join(labels, features, "driver_id", "ts", ["speed"])

        # Feature at t=1 is far too old for label at t=10000 with 1h lookback
        assert results[0]["speed"] is None

    def test_missing_entity_features(self):
        labels = [{"driver_id": "d99", "ts": 1000.0, "label": 1.0}]
        features = [{"driver_id": "d1", "ts": 900.0, "speed": 30.0}]
        joiner = PointInTimeJoiner(lookback_hours=24)
        results = joiner.join(labels, features, "driver_id", "ts", ["speed"])
        assert results[0]["speed"] is None

    def test_validate_no_leakage_clean(self):
        joiner = PointInTimeJoiner()
        data = [{"ts": 1000.0, "feature_time": 900.0}]
        violations = joiner.validate_no_leakage(data, "ts", "feature_time")
        assert violations == []

    def test_validate_no_leakage_detects_leak(self):
        joiner = PointInTimeJoiner()
        data = [{"ts": 1000.0, "feature_time": 1100.0}]
        violations = joiner.validate_no_leakage(data, "ts", "feature_time")
        assert len(violations) == 1
        assert violations[0]["leak_seconds"] == 100.0

    def test_negative_lookback_raises(self):
        with pytest.raises(ValueError):
            PointInTimeJoiner(lookback_hours=-1)


# ===== NaiveJoiner Tests =====

class TestNaiveJoiner:

    def test_naive_joiner_uses_latest(self):
        labels = [{"driver_id": "d1", "ts": 1000.0, "label": 25.0}]
        features = [
            {"driver_id": "d1", "ts": 900.0, "speed": 35.0},
            {"driver_id": "d1", "ts": 1500.0, "speed": 20.0},
        ]
        joiner = NaiveJoiner()
        results = joiner.join(labels, features, "driver_id", ["speed"])

        # NaiveJoiner uses latest (20.0) -- this is data leakage!
        assert results[0]["speed"] == 20.0


# ===== BucketTransform Tests =====

class TestBucketTransform:

    def test_basic_bucketing(self):
        bt = BucketTransform([10, 50, 100])
        assert bt.transform(5) == "bucket_0"
        assert bt.transform(25) == "bucket_1"
        assert bt.transform(75) == "bucket_2"
        assert bt.transform(150) == "bucket_3"

    def test_labeled_buckets(self):
        bt = BucketTransform([10, 50], labels=["low", "medium", "high"])
        assert bt.transform(5) == "low"
        assert bt.transform(30) == "medium"
        assert bt.transform(100) == "high"

    def test_batch_transform(self):
        bt = BucketTransform([10, 50])
        results = bt.transform_batch([5, 25, 75])
        assert len(results) == 3

    def test_wrong_label_count_raises(self):
        with pytest.raises(ValueError):
            BucketTransform([10, 50], labels=["a", "b"])

    def test_unsorted_boundaries_raises(self):
        with pytest.raises(ValueError):
            BucketTransform([50, 10])

    def test_empty_boundaries_raises(self):
        with pytest.raises(ValueError):
            BucketTransform([])


# ===== LogTransform Tests =====

class TestLogTransform:

    def test_transform(self):
        lt = LogTransform()
        assert lt.transform(0) == 0.0
        assert abs(lt.transform(math.e - 1) - 1.0) < 1e-10

    def test_inverse(self):
        lt = LogTransform()
        original = 42.0
        assert abs(lt.inverse(lt.transform(original)) - original) < 1e-10

    def test_negative_raises(self):
        lt = LogTransform()
        with pytest.raises(ValueError):
            lt.transform(-1)


# ===== InteractionFeature Tests =====

class TestInteractionFeature:

    def test_multiply(self):
        feat = InteractionFeature("a", "b", "multiply")
        assert feat.compute({"a": 3.0, "b": 4.0}) == 12.0

    def test_add(self):
        feat = InteractionFeature("a", "b", "add")
        assert feat.compute({"a": 3.0, "b": 4.0}) == 7.0

    def test_ratio_safe_division(self):
        feat = InteractionFeature("a", "b", "ratio")
        assert feat.compute({"a": 10.0, "b": 0.0}) == 0.0

    def test_invalid_operation_raises(self):
        with pytest.raises(ValueError):
            InteractionFeature("a", "b", "power")

    def test_name_property(self):
        feat = InteractionFeature("distance", "surge", "multiply")
        assert feat.name == "distance_multiply_surge"


# ===== WindowAggregate Tests =====

class TestWindowAggregate:

    def test_mean_window(self):
        wa = WindowAggregate(window_size=3, agg_func="mean")
        result = wa.compute([10, 20, 30, 40, 50])
        # Window at position 4: [30, 40, 50] -> mean=40
        assert result[4] == 40.0

    def test_sum_window(self):
        wa = WindowAggregate(window_size=2, agg_func="sum")
        result = wa.compute([1, 2, 3])
        assert result[0] == 1  # [1]
        assert result[1] == 3  # [1, 2]
        assert result[2] == 5  # [2, 3]

    def test_std_window(self):
        wa = WindowAggregate(window_size=3, agg_func="std")
        result = wa.compute([10, 10, 10])
        assert result[2] == 0.0  # No variance

    def test_empty_values(self):
        wa = WindowAggregate(window_size=3, agg_func="mean")
        assert wa.compute([]) == []

    def test_invalid_agg_func_raises(self):
        with pytest.raises(ValueError):
            WindowAggregate(window_size=3, agg_func="median")

    def test_window_size_zero_raises(self):
        with pytest.raises(ValueError):
            WindowAggregate(window_size=0)


# ===== FreshnessChecker Tests =====

class TestFreshnessChecker:

    def test_fresh_feature(self):
        checker = FreshnessChecker()
        checker.register_sla("demand", 300.0)
        checker.update_timestamp("demand", 1000.0)
        result = checker.check_freshness("demand", 1200.0)
        assert result["fresh"] is True
        assert result["status"] == "fresh"
        assert result["age_seconds"] == 200.0

    def test_stale_feature(self):
        checker = FreshnessChecker()
        checker.register_sla("demand", 300.0)
        checker.update_timestamp("demand", 1000.0)
        result = checker.check_freshness("demand", 1400.0)
        assert result["fresh"] is False
        assert result["status"] == "stale"

    def test_unknown_feature(self):
        checker = FreshnessChecker()
        checker.register_sla("demand", 300.0)
        # Never updated
        result = checker.check_freshness("demand", 1000.0)
        assert result["status"] == "unknown"
        assert result["age_seconds"] is None

    def test_check_all(self):
        checker = FreshnessChecker()
        checker.register_sla("a", 100.0)
        checker.register_sla("b", 200.0)
        checker.update_timestamp("a", 900.0)
        checker.update_timestamp("b", 900.0)
        results = checker.check_all(1000.0)
        assert len(results) == 2
        assert results[0]["feature"] == "a"

    def test_get_violations(self):
        checker = FreshnessChecker()
        checker.register_sla("fresh_one", 1000.0)
        checker.register_sla("stale_one", 10.0)
        checker.update_timestamp("fresh_one", 990.0)
        checker.update_timestamp("stale_one", 900.0)
        violations = checker.get_violations(1000.0)
        assert len(violations) == 1
        assert violations[0]["feature"] == "stale_one"

    def test_unregistered_update_raises(self):
        checker = FreshnessChecker()
        with pytest.raises(KeyError):
            checker.update_timestamp("unknown", 1000.0)

    def test_unregistered_check_raises(self):
        checker = FreshnessChecker()
        with pytest.raises(KeyError):
            checker.check_freshness("unknown", 1000.0)

    def test_negative_sla_raises(self):
        checker = FreshnessChecker()
        with pytest.raises(ValueError):
            checker.register_sla("x", -10.0)
