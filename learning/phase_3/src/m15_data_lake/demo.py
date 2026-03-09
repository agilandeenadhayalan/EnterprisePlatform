"""
Demo: Data Lake Architecture Concepts
========================================

Runs demonstrations of medallion architecture, Parquet concepts,
and lakehouse time travel.
"""

from m15_data_lake.medallion import (
    BronzeLayer,
    SilverLayer,
    GoldLayer,
    MedallionPipeline,
)
from m15_data_lake.parquet_io import (
    ParquetSchema,
    ColumnDef,
    ParquetWriter,
    ParquetReader,
    SchemaEvolution,
)
from m15_data_lake.lakehouse import (
    TableFormat,
    TimeTravel,
    Lakehouse,
)


def demo_medallion() -> None:
    print("=" * 60)
    print("MEDALLION ARCHITECTURE")
    print("=" * 60)

    raw_data = [
        {"ride_id": "r1", "zone": "Manhattan", "fare": "25.50", "distance": "5.2"},
        {"ride_id": "r2", "zone": "Brooklyn", "fare": "18.00", "distance": "3.5"},
        {"ride_id": "r3", "zone": "Manhattan", "fare": None, "distance": "4.0"},
        {"ride_id": "r1", "zone": "Manhattan", "fare": "25.50", "distance": "5.2"},  # dup
        {"ride_id": "r4", "zone": "Queens", "fare": "999.00", "distance": "2.0"},  # outlier
    ]

    pipeline = MedallionPipeline(
        required_fields=["ride_id", "zone", "fare"],
        type_conversions={"fare": float, "distance": float},
        value_ranges={"fare": (0, 200), "distance": (0, 100)},
        group_by=["zone"],
        metrics={"fare": "sum", "distance": "avg"},
    )
    stats = pipeline.run(raw_data, source="ride-api")

    print(f"\nPipeline Stats:")
    for key, val in stats.items():
        print(f"  {key}: {val}")

    print(f"\nBronze records: {pipeline.bronze.count}")
    print(f"Silver records: {pipeline.silver.count}")
    print(f"Gold groups:")
    for record in pipeline.gold.records:
        print(f"  {record.group_key} -> {record.metrics}")


def demo_parquet() -> None:
    print("\n" + "=" * 60)
    print("PARQUET CONCEPTS")
    print("=" * 60)

    schema = ParquetSchema([
        ColumnDef("ride_id", "string", nullable=False),
        ColumnDef("zone", "string"),
        ColumnDef("fare", "float"),
        ColumnDef("distance", "float"),
    ])

    writer = ParquetWriter(schema, row_group_size=3, partition_columns=["zone"])
    records = [
        {"ride_id": "r1", "zone": "Manhattan", "fare": 25.0, "distance": 5.2},
        {"ride_id": "r2", "zone": "Manhattan", "fare": 35.0, "distance": 8.1},
        {"ride_id": "r3", "zone": "Brooklyn", "fare": 18.0, "distance": 3.5},
        {"ride_id": "r4", "zone": "Brooklyn", "fare": 22.0, "distance": 4.0},
    ]
    written = writer.write(records)
    print(f"\nWrote {written} records across partitions: {writer.partition_keys}")

    reader = ParquetReader(writer)
    results, stats = reader.read(
        columns=["ride_id", "fare"],  # Column pruning
        predicates={"fare": ("gte", 20.0)},  # Predicate pushdown
    )
    print(f"\nQuery: columns=[ride_id, fare], fare >= 20.0")
    print(f"  Stats: {stats}")
    for row in results:
        print(f"  {row}")

    # Schema evolution
    print("\n--- Schema Evolution ---")
    new_col = ColumnDef("tip", "float", nullable=True)
    new_schema = SchemaEvolution.add_column(schema, new_col)
    compatible, issues = SchemaEvolution.is_backward_compatible(schema, new_schema)
    print(f"  Added 'tip' column. Backward compatible: {compatible}")


def demo_time_travel() -> None:
    print("\n" + "=" * 60)
    print("LAKEHOUSE TIME TRAVEL")
    print("=" * 60)

    table = TableFormat("rides")
    table.append([
        {"ride_id": "r1", "fare": 25.0},
        {"ride_id": "r2", "fare": 30.0},
    ])
    print(f"\nVersion 1: {len(table.current_records)} records")

    table.append([{"ride_id": "r3", "fare": 15.0}])
    print(f"Version 2: {len(table.current_records)} records")

    table.delete({"ride_id": "r1"})
    print(f"Version 3 (after delete): {len(table.current_records)} records")

    tt = TimeTravel(table)
    v1_data = tt.as_of_version(1)
    print(f"\nTime travel to version 1: {v1_data}")

    diff = tt.diff(1, 3)
    print(f"\nDiff v1 -> v3:")
    print(f"  Added: {diff['added']}")
    print(f"  Removed: {diff['removed']}")

    print(f"\nOperation history:")
    for entry in tt.history:
        print(f"  v{entry['version']}: {entry['operation']} "
              f"(+{entry['records_added']}, -{entry['records_removed']})")


if __name__ == "__main__":
    demo_medallion()
    demo_parquet()
    demo_time_travel()
