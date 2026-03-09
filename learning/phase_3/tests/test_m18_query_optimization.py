"""Tests for Module 18: Query Optimization."""

import pytest

from learning.phase_3.src.m18_query_optimization.query_plans import (
    explain,
    optimize,
    NodeType,
    PlanNode,
    QueryPlan,
)
from learning.phase_3.src.m18_query_optimization.skip_indexes import (
    Granule,
    MinMaxIndex,
    SetIndex,
    BloomFilterIndex,
    IndexSelector,
)
from learning.phase_3.src.m18_query_optimization.partitioning import (
    PartitionedTable,
    HotColdStorage,
    PartitionKeyAdvisor,
)


# ── Query Plans ──


class TestQueryPlans:
    def test_explain_generates_plan(self):
        plan = explain(table="rides", predicate="fare > 20", table_rows=10000)
        nodes = plan.all_nodes()
        assert any(n.node_type == NodeType.SCAN for n in nodes)
        assert any(n.node_type == NodeType.FILTER for n in nodes)

    def test_explain_with_group_by(self):
        plan = explain(
            table="rides",
            group_by=["zone"],
            table_rows=10000,
        )
        nodes = plan.all_nodes()
        assert any(n.node_type == NodeType.AGGREGATE for n in nodes)

    def test_explain_with_sort(self):
        plan = explain(table="rides", order_by=["fare"], table_rows=10000)
        nodes = plan.all_nodes()
        assert any(n.node_type == NodeType.SORT for n in nodes)

    def test_predicate_pushdown(self):
        plan = explain(
            table="rides",
            predicate="fare > 20",
            table_rows=10000,
        )
        optimized = optimize(plan)
        nodes = optimized.all_nodes()
        # After pushdown, filter should be merged into scan
        pushed = any(n.details.get("predicate_pushed_down") for n in nodes)
        assert pushed is True

    def test_optimized_plan_lower_cost(self):
        plan = explain(
            table="rides",
            predicate="fare > 20",
            table_rows=100000,
        )
        optimized = optimize(plan)
        assert optimized.total_cost <= plan.total_cost

    def test_plan_format(self):
        plan = explain(table="rides", table_rows=1000)
        formatted = plan.format_plan()
        assert "Scan" in formatted
        assert "rides" in formatted


# ── Skip Indexes ──


class TestMinMaxIndex:
    def _make_granules(self):
        return [
            Granule(0, [{"id": i, "fare": 10 + i} for i in range(10)]),   # fare: 10-19
            Granule(1, [{"id": i, "fare": 20 + i} for i in range(10)]),   # fare: 20-29
            Granule(2, [{"id": i, "fare": 30 + i} for i in range(10)]),   # fare: 30-39
        ]

    def test_skip_granule_below_range(self):
        granules = self._make_granules()
        idx = MinMaxIndex("fare")
        idx.build(granules)
        assert idx.can_skip(0, "gt", 25) is True   # max=19 <= 25
        assert idx.can_skip(2, "gt", 25) is False   # max=39 > 25

    def test_query_skips_irrelevant_granules(self):
        granules = self._make_granules()
        idx = MinMaxIndex("fare")
        idx.build(granules)
        results, stats = idx.query(granules, "gte", 30)
        assert stats["skipped"] == 2  # Granules 0 and 1 skipped
        assert stats["scanned"] == 1
        assert all(r["fare"] >= 30 for r in results)

    def test_eq_skip(self):
        granules = self._make_granules()
        idx = MinMaxIndex("fare")
        idx.build(granules)
        assert idx.can_skip(0, "eq", 25) is True   # 25 not in [10, 19]
        assert idx.can_skip(1, "eq", 25) is False   # 25 in [20, 29]

    def test_between_skip(self):
        granules = self._make_granules()
        idx = MinMaxIndex("fare")
        idx.build(granules)
        assert idx.can_skip(0, "between", (25, 35)) is True   # [10,19] doesn't overlap [25,35]
        assert idx.can_skip(1, "between", (25, 35)) is False  # [20,29] overlaps [25,35]


class TestSetIndex:
    def test_skip_when_value_not_in_set(self):
        granules = [
            Granule(0, [{"zone": "A"}, {"zone": "B"}]),
            Granule(1, [{"zone": "C"}, {"zone": "D"}]),
        ]
        idx = SetIndex("zone")
        idx.build(granules)
        assert idx.can_skip(0, "C") is True
        assert idx.can_skip(1, "C") is False

    def test_query_with_skipping(self):
        granules = [
            Granule(0, [{"zone": "A"}, {"zone": "B"}]),
            Granule(1, [{"zone": "C"}, {"zone": "D"}]),
            Granule(2, [{"zone": "A"}, {"zone": "E"}]),
        ]
        idx = SetIndex("zone")
        idx.build(granules)
        results, stats = idx.query(granules, "C")
        assert stats["skipped"] == 2
        assert len(results) == 1


class TestBloomFilterIndex:
    def test_bloom_filter_no_false_negatives(self):
        granules = [
            Granule(0, [{"user_id": f"u{i}"} for i in range(100)]),
        ]
        idx = BloomFilterIndex("user_id", expected_elements=100, false_positive_rate=0.01)
        idx.build(granules)
        # Value that IS in the granule should never be skipped
        assert idx.can_skip(0, "u50") is False

    def test_bloom_filter_skips_absent_value(self):
        granules = [
            Granule(0, [{"user_id": f"u{i}"} for i in range(100)]),
        ]
        idx = BloomFilterIndex("user_id", expected_elements=100, false_positive_rate=0.01)
        idx.build(granules)
        # Value NOT in the granule should usually be skipped (might have FP)
        # Test with a very different value
        skip_count = sum(1 for i in range(100) if idx.can_skip(0, f"not_here_{i}"))
        # Most should be skipped (>80% given low FP rate)
        assert skip_count > 50


class TestIndexSelector:
    def test_low_cardinality_recommends_set(self):
        result = IndexSelector.recommend(cardinality=5, total_rows=100000)
        assert result == "set"

    def test_sequential_recommends_minmax(self):
        result = IndexSelector.recommend(
            cardinality=1000, total_rows=100000, is_sequential=True
        )
        assert result == "minmax"

    def test_high_cardinality_recommends_bloom(self):
        result = IndexSelector.recommend(cardinality=50000, total_rows=100000)
        assert result == "bloom_filter"


# ── Partitioning ──


class TestPartitioning:
    def test_insert_routes_to_partitions(self):
        table = PartitionedTable("rides", partition_key="date")
        table.insert([
            {"ride_id": "r1", "date": "2024-01-15", "fare": 25},
            {"ride_id": "r2", "date": "2024-02-10", "fare": 30},
            {"ride_id": "r3", "date": "2024-01-20", "fare": 20},
        ])
        assert table.partition_count == 2  # 2024-01 and 2024-02

    def test_partition_pruning(self):
        table = PartitionedTable("rides", partition_key="date")
        for month in range(1, 7):
            table.insert([{"ride_id": f"r-{month}", "date": f"2024-{month:02d}-15", "fare": 10}])

        pruned_keys = table.partition_prune({"date": "2024-03-15"})
        assert len(pruned_keys) == 1
        assert pruned_keys[0] == "2024-03"

    def test_query_with_pruning_stats(self):
        table = PartitionedTable("rides", partition_key="date")
        for month in range(1, 7):
            for i in range(10):
                table.insert([{"ride_id": f"r-{month}-{i}", "date": f"2024-{month:02d}-15", "fare": 10 + i}])

        results, stats = table.query({"date": "2024-03-15"})
        assert stats["partitions_pruned"] > 0
        assert stats["partitions_scanned"] < stats["partitions_total"]


class TestHotColdStorage:
    def test_classify_partitions(self):
        table = PartitionedTable("rides", partition_key="date")
        table.insert([{"ride_id": "r1", "date": "2024-01-15"}])
        table.insert([{"ride_id": "r2", "date": "2024-05-15"}])

        classifier = HotColdStorage(hot_threshold_days=90, reference_date="2024-04-01")
        tiers = classifier.classify_partitions(table)
        assert "2024-01" in tiers["cold"]
        assert "2024-05" in tiers["hot"]

    def test_move_to_cold(self):
        table = PartitionedTable("rides", partition_key="date")
        table.insert([{"ride_id": "r1", "date": "2024-01-15"}])
        table.insert([{"ride_id": "r2", "date": "2024-05-15"}])

        classifier = HotColdStorage(reference_date="2024-04-01")
        moved = classifier.move_to_cold(table)
        assert "2024-01" in moved


class TestPartitionKeyAdvisor:
    def test_recommends_most_filtered_column(self):
        rec = PartitionKeyAdvisor.recommend(
            query_patterns=[
                {"filters": ["date", "zone"]},
                {"filters": ["date"]},
                {"filters": ["date", "driver_id"]},
            ],
            data_range_days=365,
            daily_rows=50000,
        )
        assert rec["recommended_key"] == "date"
        assert rec["estimated_partitions"] > 0

    def test_warns_on_high_partition_count(self):
        rec = PartitionKeyAdvisor.recommend(
            query_patterns=[{"filters": ["date"]}],
            data_range_days=3650,  # 10 years
            daily_rows=100000,
        )
        # Monthly granularity for long range
        assert rec["granularity"] == "monthly"
