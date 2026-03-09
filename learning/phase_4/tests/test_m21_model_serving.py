"""
Tests for Module 21: Model Serving Patterns.
~25 tests covering request_batching, model_router, model_warmup,
and inference_cache.
"""

import pytest

from m21_model_serving.request_batching import RequestBatcher
from m21_model_serving.model_router import ABTestRouter, ShadowRouter, CanaryRouter
from m21_model_serving.model_warmup import ModelWarmer
from m21_model_serving.inference_cache import PredictionCache


# ===== RequestBatcher Tests =====

class TestRequestBatcher:

    def test_add_and_flush(self):
        batcher = RequestBatcher(max_batch_size=3, max_wait_ms=100.0)
        batcher.add_request("r1", {"x": 1}, 1000.0)
        batcher.add_request("r2", {"x": 2}, 1000.01)
        batch = batcher.flush()
        assert len(batch) == 2
        assert batch[0]["request_id"] == "r1"

    def test_flush_empty_returns_empty(self):
        batcher = RequestBatcher()
        assert batcher.flush() == []

    def test_should_flush_on_batch_size(self):
        batcher = RequestBatcher(max_batch_size=2, max_wait_ms=1000.0)
        batcher.add_request("r1", {}, 1000.0)
        assert not batcher.should_flush(1000.0)
        batcher.add_request("r2", {}, 1000.01)
        assert batcher.should_flush(1000.01)

    def test_should_flush_on_timeout(self):
        batcher = RequestBatcher(max_batch_size=100, max_wait_ms=50.0)
        batcher.add_request("r1", {}, 1000.0)
        assert not batcher.should_flush(1000.01)
        assert batcher.should_flush(1000.06)  # 60ms > 50ms

    def test_should_flush_empty_returns_false(self):
        batcher = RequestBatcher()
        assert not batcher.should_flush(9999.0)

    def test_stats(self):
        batcher = RequestBatcher(max_batch_size=2, max_wait_ms=100.0)
        batcher.add_request("r1", {}, 1000.0)
        batcher.add_request("r2", {}, 1000.01)
        batcher.flush()
        stats = batcher.stats()
        assert stats["batch_count"] == 1
        assert stats["total_requests"] == 2
        assert stats["avg_batch_size"] == 2.0

    def test_pending_count(self):
        batcher = RequestBatcher()
        assert batcher.pending_count() == 0
        batcher.add_request("r1", {}, 1.0)
        assert batcher.pending_count() == 1
        batcher.flush()
        assert batcher.pending_count() == 0

    def test_invalid_max_batch_size_raises(self):
        with pytest.raises(ValueError):
            RequestBatcher(max_batch_size=0)

    def test_invalid_max_wait_raises(self):
        with pytest.raises(ValueError):
            RequestBatcher(max_wait_ms=-1.0)


# ===== ABTestRouter Tests =====

class TestABTestRouter:

    def test_deterministic_routing(self):
        router = ABTestRouter("v1", "v2", traffic_split=0.3)
        result1 = router.route("req_abc")
        result2 = router.route("req_abc")
        assert result1 == result2

    def test_traffic_split_approximate(self):
        router = ABTestRouter("v1", "v2", traffic_split=0.5)
        results = {"v1": 0, "v2": 0}
        for i in range(1000):
            model = router.route(f"req_{i}")
            results[model] += 1
        # With 50% split, both should be roughly equal
        assert 350 < results["v2"] < 650

    def test_record_and_get_metrics(self):
        router = ABTestRouter("v1", "v2", traffic_split=0.5)
        router.record_outcome("req1", "v1", 10.0)
        router.record_outcome("req2", "v1", 20.0)
        router.record_outcome("req3", "v2", 15.0)
        metrics = router.get_metrics()
        assert metrics["v1"]["count"] == 2
        assert metrics["v1"]["mean"] == 15.0
        assert metrics["v2"]["count"] == 1

    def test_invalid_traffic_split_raises(self):
        with pytest.raises(ValueError):
            ABTestRouter("a", "b", traffic_split=1.5)


# ===== ShadowRouter Tests =====

class TestShadowRouter:

    def test_routes_to_both(self):
        router = ShadowRouter("primary", "shadow")
        primary, shadow = router.route("req_1")
        assert primary == "primary"
        assert shadow == "shadow"

    def test_record_comparison(self):
        router = ShadowRouter("primary", "shadow")
        router.route("req_1")
        router.record_comparison("req_1", 10.0, 12.0)
        stats = router.get_divergence_stats()
        assert stats["count"] == 1
        assert stats["mean_diff"] == 2.0

    def test_empty_divergence_stats(self):
        router = ShadowRouter("p", "s")
        stats = router.get_divergence_stats()
        assert stats["count"] == 0


# ===== CanaryRouter Tests =====

class TestCanaryRouter:

    def test_promote_increases_traffic(self):
        router = CanaryRouter("stable", "canary", initial_pct=1.0, step_pct=5.0)
        assert router.current_pct == 1.0
        router.promote()
        assert router.current_pct == 6.0
        router.promote()
        assert router.current_pct == 11.0

    def test_promote_respects_max(self):
        router = CanaryRouter(
            "stable", "canary",
            initial_pct=95.0, max_pct=100.0, step_pct=10.0,
        )
        router.promote()
        assert router.current_pct == 100.0

    def test_rollback(self):
        router = CanaryRouter("stable", "canary", initial_pct=10.0)
        router.promote()
        router.rollback()
        assert router.current_pct == 0.0

    def test_promotion_history(self):
        router = CanaryRouter("stable", "canary", initial_pct=1.0, step_pct=5.0)
        router.promote()
        router.promote()
        assert router.promotion_history == [1.0, 6.0, 11.0]

    def test_is_fully_rolled_out(self):
        router = CanaryRouter("s", "c", initial_pct=100.0, max_pct=100.0)
        assert router.is_fully_rolled_out

    def test_deterministic_routing(self):
        router = CanaryRouter("s", "c", initial_pct=50.0)
        r1 = router.route("req_1")
        r2 = router.route("req_1")
        assert r1 == r2


# ===== ModelWarmer Tests =====

class TestModelWarmer:

    def _dummy_predict(self, features: dict) -> float:
        return sum(features.values())

    def test_register_and_warmup(self):
        warmer = ModelWarmer()
        warmer.register_model(
            "model_v1",
            self._dummy_predict,
            [{"x": 1.0}, {"x": 2.0}, {"x": 3.0}],
        )
        stats = warmer.warmup("model_v1")
        assert stats["name"] == "model_v1"
        assert stats["num_warmup_calls"] == 3
        assert stats["avg_warmup_latency_ms"] >= 0
        assert warmer.is_warm("model_v1")

    def test_not_warm_before_warmup(self):
        warmer = ModelWarmer()
        warmer.register_model("m", self._dummy_predict, [{"x": 1}])
        assert not warmer.is_warm("m")

    def test_warmup_all(self):
        warmer = ModelWarmer()
        warmer.register_model("m1", self._dummy_predict, [{"x": 1}])
        warmer.register_model("m2", self._dummy_predict, [{"x": 2}])
        results = warmer.warmup_all()
        assert len(results) == 2
        assert warmer.is_warm("m1")
        assert warmer.is_warm("m2")

    def test_unregistered_warmup_raises(self):
        warmer = ModelWarmer()
        with pytest.raises(KeyError):
            warmer.warmup("nonexistent")

    def test_unregistered_is_warm_raises(self):
        warmer = ModelWarmer()
        with pytest.raises(KeyError):
            warmer.is_warm("nonexistent")

    def test_empty_warmup_inputs_raises(self):
        warmer = ModelWarmer()
        with pytest.raises(ValueError):
            warmer.register_model("m", self._dummy_predict, [])


# ===== PredictionCache Tests =====

class TestPredictionCache:

    def test_put_and_get(self):
        cache = PredictionCache(max_size=10, ttl_seconds=60.0)
        cache.put("key1", {"value": 42.0}, current_time=1000.0)
        result = cache.get("key1", current_time=1010.0)
        assert result == {"value": 42.0}

    def test_miss_returns_none(self):
        cache = PredictionCache()
        assert cache.get("missing", current_time=1.0) is None

    def test_ttl_expiration(self):
        cache = PredictionCache(ttl_seconds=10.0)
        cache.put("key1", {"v": 1}, current_time=1000.0)
        assert cache.get("key1", current_time=1005.0) is not None
        assert cache.get("key1", current_time=1015.0) is None

    def test_lru_eviction(self):
        cache = PredictionCache(max_size=2, ttl_seconds=600.0)
        cache.put("k1", {"v": 1}, current_time=1.0)
        cache.put("k2", {"v": 2}, current_time=2.0)
        cache.put("k3", {"v": 3}, current_time=3.0)  # k1 evicted (LRU)
        assert cache.get("k1", current_time=4.0) is None
        assert cache.get("k2", current_time=4.0) == {"v": 2}

    def test_make_key_deterministic(self):
        cache = PredictionCache()
        key1 = cache.make_key("model_v1", {"a": 1, "b": 2})
        key2 = cache.make_key("model_v1", {"b": 2, "a": 1})
        assert key1 == key2  # Dict order shouldn't matter

    def test_make_key_different_models(self):
        cache = PredictionCache()
        key1 = cache.make_key("model_v1", {"a": 1})
        key2 = cache.make_key("model_v2", {"a": 1})
        assert key1 != key2

    def test_stats(self):
        cache = PredictionCache(max_size=10, ttl_seconds=600.0)
        cache.put("k1", {"v": 1}, current_time=1.0)
        cache.get("k1", current_time=2.0)  # Hit
        cache.get("k2", current_time=2.0)  # Miss
        stats = cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5
        assert stats["size"] == 1

    def test_clear(self):
        cache = PredictionCache()
        cache.put("k1", {"v": 1}, current_time=1.0)
        cache.clear()
        assert cache.get("k1", current_time=2.0) is None
        assert cache.stats()["size"] == 0

    def test_update_existing_key(self):
        cache = PredictionCache(max_size=10, ttl_seconds=600.0)
        cache.put("k1", {"v": 1}, current_time=1.0)
        cache.put("k1", {"v": 2}, current_time=2.0)
        result = cache.get("k1", current_time=3.0)
        assert result == {"v": 2}

    def test_invalid_max_size_raises(self):
        with pytest.raises(ValueError):
            PredictionCache(max_size=0)

    def test_invalid_ttl_raises(self):
        with pytest.raises(ValueError):
            PredictionCache(ttl_seconds=-1.0)
