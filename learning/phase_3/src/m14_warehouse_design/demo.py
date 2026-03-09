"""
Demo: Analytics Warehouse Design Concepts
============================================

Runs demonstrations of star schema modeling, MergeTree engines,
and materialized views.
"""

from m14_warehouse_design.star_schema import (
    FactTable,
    DimensionTable,
    StarSchema,
)
from m14_warehouse_design.merge_tree import (
    MergeTree,
    ReplacingMergeTree,
    SummingMergeTree,
    AggregatingMergeTree,
)
from m14_warehouse_design.materialized_views import (
    MaterializedView,
    AggregationSpec,
    RefreshStrategy,
)


def demo_star_schema() -> None:
    print("=" * 60)
    print("STAR SCHEMA MODELING")
    print("=" * 60)

    # Create dimensions
    dim_zones = DimensionTable("zones", "zone_id")
    dim_zones.add("z1", {"zone_name": "Manhattan", "borough": "Manhattan", "area_sq_km": 59.1})
    dim_zones.add("z2", {"zone_name": "Brooklyn", "borough": "Brooklyn", "area_sq_km": 183.4})

    dim_drivers = DimensionTable("drivers", "driver_id")
    dim_drivers.add("d1", {"driver_name": "Alice", "vehicle_type": "sedan", "rating": 4.8})
    dim_drivers.add("d2", {"driver_name": "Bob", "vehicle_type": "suv", "rating": 4.5})

    # Create fact table
    fact_rides = FactTable(
        "fact_rides",
        dimension_keys=["zone_id", "driver_id"],
        measures=["fare", "distance_km", "duration_min"],
    )
    fact_rides.add_fact({"zone_id": "z1", "driver_id": "d1", "fare": 25.0, "distance_km": 5.2, "duration_min": 15})
    fact_rides.add_fact({"zone_id": "z1", "driver_id": "d2", "fare": 35.0, "distance_km": 8.1, "duration_min": 22})
    fact_rides.add_fact({"zone_id": "z2", "driver_id": "d1", "fare": 18.0, "distance_km": 3.5, "duration_min": 10})

    # Star schema queries
    schema = StarSchema(fact_rides)
    schema.add_dimension("zone_id", dim_zones)
    schema.add_dimension("driver_id", dim_drivers)

    print("\nDenormalized Query (all rides with dimension attributes):")
    for row in schema.denormalized_query():
        print(f"  {row}")

    print("\nAggregate: total fare by zone:")
    for row in fact_rides.aggregate(["zone_id"], "fare", "sum"):
        print(f"  {row}")

    # SCD Type 2
    print("\n--- SCD Type 2 Update ---")
    print(f"Before: {dim_drivers.lookup('d1').attributes}")
    dim_drivers.scd_type2_update("d1", {"vehicle_type": "luxury", "rating": 4.9})
    print(f"After:  {dim_drivers.lookup('d1').attributes}")
    print(f"History for d1: {len(dim_drivers.history('d1'))} versions")


def demo_merge_tree() -> None:
    print("\n" + "=" * 60)
    print("MERGETREE ENGINE FAMILY")
    print("=" * 60)

    # ReplacingMergeTree
    print("\n--- ReplacingMergeTree ---")
    rmt = ReplacingMergeTree(primary_key=["ride_id"], version_column="version")
    rmt.insert([{"ride_id": "r1", "fare": 25.0, "version": 1}])
    rmt.insert([{"ride_id": "r1", "fare": 30.0, "version": 2}])  # Updated fare
    print(f"Before merge: {len(rmt.query())} rows (both versions)")
    rmt.merge()
    print(f"After merge:  {len(rmt.query())} row (latest version only)")
    print(f"  Result: {rmt.query()}")

    # SummingMergeTree
    print("\n--- SummingMergeTree ---")
    smt = SummingMergeTree(primary_key=["zone", "date"], sum_columns=["rides", "fare"])
    smt.insert([{"zone": "A", "date": "2024-01-01", "rides": 5, "fare": 100}])
    smt.insert([{"zone": "A", "date": "2024-01-01", "rides": 3, "fare": 60}])
    smt.insert([{"zone": "B", "date": "2024-01-01", "rides": 7, "fare": 140}])
    print(f"Before merge: {smt.total_rows} rows")
    smt.merge()
    print(f"After merge:  {smt.total_rows} rows")
    for row in smt.query():
        print(f"  {row}")


def demo_materialized_views() -> None:
    print("\n" + "=" * 60)
    print("MATERIALIZED VIEWS")
    print("=" * 60)

    mv = MaterializedView(
        name="rides_by_zone",
        aggregation=AggregationSpec(
            group_by=["zone"],
            aggregations={"fare": "sum", "distance": "sum"},
        ),
    )

    # Simulate inserting batches
    batch1 = [
        {"zone": "Manhattan", "fare": 25.0, "distance": 5.2},
        {"zone": "Manhattan", "fare": 35.0, "distance": 8.1},
        {"zone": "Brooklyn", "fare": 18.0, "distance": 3.5},
    ]
    mv.on_insert(batch1)
    print(f"\nAfter batch 1 ({len(batch1)} rows):")
    for row in mv.query():
        print(f"  {row}")

    batch2 = [
        {"zone": "Manhattan", "fare": 42.0, "distance": 10.0},
        {"zone": "Queens", "fare": 22.0, "distance": 6.0},
    ]
    mv.on_insert(batch2)
    print(f"\nAfter batch 2 ({len(batch2)} rows) — incremental update:")
    for row in mv.query():
        print(f"  {row}")

    print(f"\nTotal rows processed: {mv.rows_processed}")
    print("(MV only processed new rows, not re-scanned existing data)")


if __name__ == "__main__":
    demo_star_schema()
    demo_merge_tree()
    demo_materialized_views()
