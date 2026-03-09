"""Tests for Module 14: Analytics Warehouse Design."""

import pytest

from learning.phase_3.src.m14_warehouse_design.star_schema import (
    FactTable,
    DimensionTable,
    StarSchema,
)
from learning.phase_3.src.m14_warehouse_design.merge_tree import (
    MergeTree,
    ReplacingMergeTree,
    SummingMergeTree,
    AggregatingMergeTree,
)
from learning.phase_3.src.m14_warehouse_design.materialized_views import (
    MaterializedView,
    AggregationSpec,
    RefreshStrategy,
)


# ── Star Schema ──


class TestDimensionTable:
    def test_add_and_lookup(self):
        dim = DimensionTable("zones", "zone_id")
        dim.add("z1", {"zone_name": "Manhattan", "borough": "Manhattan"})
        record = dim.lookup("z1")
        assert record is not None
        assert record.attributes["zone_name"] == "Manhattan"

    def test_lookup_missing_returns_none(self):
        dim = DimensionTable("zones", "zone_id")
        assert dim.lookup("z999") is None

    def test_scd_type2_preserves_history(self):
        dim = DimensionTable("drivers", "driver_id")
        dim.add("d1", {"name": "Alice", "vehicle": "sedan"})
        closed, new = dim.scd_type2_update("d1", {"vehicle": "luxury"})
        assert closed.is_current is False
        assert closed.valid_to is not None
        assert new.is_current is True
        assert new.attributes["vehicle"] == "luxury"
        assert len(dim.history("d1")) == 2

    def test_scd_type2_update_nonexistent_raises(self):
        dim = DimensionTable("drivers", "driver_id")
        with pytest.raises(KeyError):
            dim.scd_type2_update("d999", {"vehicle": "luxury"})


class TestFactTable:
    def test_add_and_query(self):
        fact = FactTable("rides", ["zone_id"], ["fare"])
        fact.add_fact({"zone_id": "z1", "fare": 25.0})
        fact.add_fact({"zone_id": "z2", "fare": 18.0})
        results = fact.query({"zone_id": "z1"})
        assert len(results) == 1
        assert results[0]["fare"] == 25.0

    def test_missing_dimension_key_raises(self):
        fact = FactTable("rides", ["zone_id"], ["fare"])
        with pytest.raises(ValueError, match="Missing dimension key"):
            fact.add_fact({"fare": 25.0})

    def test_aggregate_sum(self):
        fact = FactTable("rides", ["zone_id"], ["fare"])
        fact.add_fact({"zone_id": "z1", "fare": 25.0})
        fact.add_fact({"zone_id": "z1", "fare": 30.0})
        fact.add_fact({"zone_id": "z2", "fare": 18.0})
        result = fact.aggregate(["zone_id"], "fare", "sum")
        z1 = [r for r in result if r["zone_id"] == "z1"][0]
        assert z1["sum_fare"] == 55.0

    def test_aggregate_avg(self):
        fact = FactTable("rides", ["zone_id"], ["fare"])
        fact.add_fact({"zone_id": "z1", "fare": 20.0})
        fact.add_fact({"zone_id": "z1", "fare": 30.0})
        result = fact.aggregate(["zone_id"], "fare", "avg")
        assert result[0]["avg_fare"] == 25.0


class TestStarSchema:
    def test_denormalized_query_joins_dimensions(self):
        dim_zones = DimensionTable("zones", "zone_id")
        dim_zones.add("z1", {"zone_name": "Manhattan"})

        fact = FactTable("rides", ["zone_id"], ["fare"])
        fact.add_fact({"zone_id": "z1", "fare": 25.0})

        schema = StarSchema(fact)
        schema.add_dimension("zone_id", dim_zones)
        results = schema.denormalized_query()
        assert len(results) == 1
        assert results[0]["zones_zone_name"] == "Manhattan"
        assert results[0]["fare"] == 25.0


# ── MergeTree ──


class TestMergeTree:
    def test_insert_creates_parts(self):
        mt = MergeTree(primary_key=["id"])
        mt.insert([{"id": 1, "val": "a"}, {"id": 2, "val": "b"}])
        mt.insert([{"id": 3, "val": "c"}])
        assert mt.part_count == 2
        assert mt.total_rows == 3

    def test_merge_combines_parts(self):
        mt = MergeTree(primary_key=["id"])
        mt.insert([{"id": 2, "val": "b"}])
        mt.insert([{"id": 1, "val": "a"}])
        mt.merge()
        assert mt.part_count == 1
        rows = mt.query()
        assert rows[0]["id"] == 1  # Sorted by primary key

    def test_query_with_conditions(self):
        mt = MergeTree(primary_key=["id"])
        mt.insert([{"id": 1, "zone": "A"}, {"id": 2, "zone": "B"}])
        results = mt.query({"zone": "A"})
        assert len(results) == 1


class TestReplacingMergeTree:
    def test_dedup_keeps_latest_version(self):
        rmt = ReplacingMergeTree(primary_key=["id"], version_column="ver")
        rmt.insert([{"id": 1, "val": "old", "ver": 1}])
        rmt.insert([{"id": 1, "val": "new", "ver": 2}])
        rmt.merge()
        rows = rmt.query()
        assert len(rows) == 1
        assert rows[0]["val"] == "new"

    def test_final_query_deduplicates(self):
        rmt = ReplacingMergeTree(primary_key=["id"], version_column="ver")
        rmt.insert([{"id": 1, "val": "old", "ver": 1}])
        rmt.insert([{"id": 1, "val": "new", "ver": 2}])
        rows = rmt.final_query()
        assert len(rows) == 1
        assert rows[0]["val"] == "new"


class TestSummingMergeTree:
    def test_auto_sum_on_merge(self):
        smt = SummingMergeTree(primary_key=["zone"], sum_columns=["rides", "fare"])
        smt.insert([{"zone": "A", "rides": 5, "fare": 100}])
        smt.insert([{"zone": "A", "rides": 3, "fare": 60}])
        smt.merge()
        rows = smt.query()
        assert len(rows) == 1
        assert rows[0]["rides"] == 8
        assert rows[0]["fare"] == 160


# ── Materialized Views ──


class TestMaterializedView:
    def test_on_insert_incremental_update(self):
        mv = MaterializedView(
            name="rides_by_zone",
            aggregation=AggregationSpec(
                group_by=["zone"],
                aggregations={"fare": "sum"},
            ),
        )
        mv.on_insert([
            {"zone": "A", "fare": 10},
            {"zone": "A", "fare": 20},
            {"zone": "B", "fare": 15},
        ])
        results = mv.query()
        a_row = [r for r in results if r["zone"] == "A"][0]
        assert a_row["fare"] == 30
        assert mv.rows_processed == 3

    def test_incremental_second_batch(self):
        mv = MaterializedView(
            name="test",
            aggregation=AggregationSpec(
                group_by=["zone"],
                aggregations={"count": "count"},
            ),
        )
        mv.on_insert([{"zone": "A", "count": 1}])
        mv.on_insert([{"zone": "A", "count": 1}])
        results = mv.query()
        assert results[0]["count"] == 2

    def test_manual_refresh_recomputes(self):
        mv = MaterializedView(
            name="test",
            aggregation=AggregationSpec(
                group_by=["zone"],
                aggregations={"fare": "sum"},
            ),
            strategy=RefreshStrategy.MANUAL,
        )
        # on_insert should not update for MANUAL strategy
        mv.on_insert([{"zone": "A", "fare": 10}])
        assert len(mv.query()) == 0
        # Manual refresh
        mv.refresh([{"zone": "A", "fare": 10}, {"zone": "A", "fare": 20}])
        results = mv.query()
        assert results[0]["fare"] == 30
