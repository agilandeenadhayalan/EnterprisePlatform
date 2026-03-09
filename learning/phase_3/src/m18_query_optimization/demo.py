"""
Demo: Query Optimization Concepts
====================================

Runs demonstrations of query plans, skip indexes, and partitioning.
"""

from m18_query_optimization.query_plans import explain, optimize, NodeType
from m18_query_optimization.skip_indexes import (
    Granule,
    MinMaxIndex,
    SetIndex,
    BloomFilterIndex,
    IndexSelector,
)
from m18_query_optimization.partitioning import (
    PartitionedTable,
    HotColdStorage,
    PartitionKeyAdvisor,
)


def demo_query_plans() -> None:
    print("=" * 60)
    print("QUERY PLAN ANALYSIS")
    print("=" * 60)

    plan = explain(
        table="rides",
        columns=["zone", "count(*)", "sum(fare)"],
        predicate="fare > 20",
        group_by=["zone"],
        order_by=["count(*)"],
        table_rows=1000000,
    )
    print(f"\nOriginal Plan (cost={plan.total_cost:.2f}):")
    print(plan.format_plan())

    optimized = optimize(plan)
    print(f"\nOptimized Plan (cost={optimized.total_cost:.2f}):")
    print(optimized.format_plan())

    nodes = optimized.all_nodes()
    pushed_down = any(n.details.get("predicate_pushed_down") for n in nodes)
    print(f"\nPredicate pushed down: {pushed_down}")


def demo_skip_indexes() -> None:
    print("\n" + "=" * 60)
    print("SKIP INDEXES")
    print("=" * 60)

    # Create granules with sorted data
    granules = [
        Granule(0, [{"id": i, "zone": ["Manhattan", "Brooklyn", "Queens"][i % 3], "fare": 10 + i}
                     for i in range(100)]),
        Granule(1, [{"id": i, "zone": ["Manhattan", "Brooklyn"][i % 2], "fare": 110 + i}
                     for i in range(100)]),
        Granule(2, [{"id": i, "zone": ["Queens", "Bronx"][i % 2], "fare": 210 + i}
                     for i in range(100)]),
    ]

    # MinMax index
    print("\n--- MinMax Index ---")
    mm_idx = MinMaxIndex("fare")
    mm_idx.build(granules)
    results, stats = mm_idx.query(granules, "gte", 200)
    print(f"  Query: fare >= 200")
    print(f"  Results: {len(results)} rows")
    print(f"  Granules: {stats['scanned']} scanned, {stats['skipped']} skipped")

    # Set index
    print("\n--- Set Index ---")
    set_idx = SetIndex("zone")
    set_idx.build(granules)
    results, stats = set_idx.query(granules, "Bronx")
    print(f"  Query: zone = 'Bronx'")
    print(f"  Results: {len(results)} rows")
    print(f"  Granules: {stats['scanned']} scanned, {stats['skipped']} skipped")

    # Index recommendation
    print("\n--- Index Selector ---")
    print(f"  Low cardinality (5 values): {IndexSelector.recommend(5, 100000)}")
    print(f"  High cardinality (50000 values): {IndexSelector.recommend(50000, 100000)}")
    print(f"  Sequential + range queries: {IndexSelector.recommend(1000, 100000, is_sequential=True, query_pattern='range')}")


def demo_partitioning() -> None:
    print("\n" + "=" * 60)
    print("PARTITIONING & PRUNING")
    print("=" * 60)

    table = PartitionedTable("rides", partition_key="event_date")
    rows = []
    for month in range(1, 7):
        for day in [1, 15]:
            for i in range(10):
                rows.append({
                    "ride_id": f"r-{month}-{day}-{i}",
                    "event_date": f"2024-{month:02d}-{day:02d}",
                    "fare": 20 + i,
                    "zone": ["Manhattan", "Brooklyn", "Queens"][i % 3],
                })
    table.insert(rows)

    print(f"\nTable has {table.partition_count} partitions, {table.total_rows} total rows")

    # Query with partition pruning
    results, stats = table.query({"event_date": "2024-03-01"})
    print(f"\nQuery: event_date = '2024-03-01'")
    print(f"  Partitions: {stats['partitions_scanned']} scanned of {stats['partitions_total']}")
    print(f"  Pruned: {stats['partitions_pruned']} partitions skipped")
    print(f"  Rows: {stats['rows_returned']} returned")

    # Hot/cold classification
    print("\n--- Hot/Cold Storage ---")
    classifier = HotColdStorage(hot_threshold_days=90, reference_date="2024-04-01")
    tiers = classifier.classify_partitions(table)
    print(f"  Hot partitions: {tiers['hot']}")
    print(f"  Cold partitions: {tiers['cold']}")

    # Partition key recommendation
    print("\n--- Partition Key Advisor ---")
    rec = PartitionKeyAdvisor.recommend(
        query_patterns=[
            {"filters": ["event_date", "zone"]},
            {"filters": ["event_date"]},
            {"filters": ["event_date", "driver_id"]},
        ],
        data_range_days=365,
        daily_rows=50000,
    )
    print(f"  Recommended: {rec['recommended_key']} ({rec['granularity']})")
    print(f"  Estimated partitions: {rec['estimated_partitions']}")
    print(f"  Rationale: {rec['rationale']}")


if __name__ == "__main__":
    demo_query_plans()
    demo_skip_indexes()
    demo_partitioning()
