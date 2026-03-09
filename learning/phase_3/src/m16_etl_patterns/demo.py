"""
Demo: ETL/ELT Pipeline Patterns
==================================

Runs demonstrations of DAG scheduling, incremental loading,
CDC, and SCD Type 2.
"""

from m16_etl_patterns.dag_scheduler import DAG, Task
from m16_etl_patterns.incremental_load import IncrementalLoader, WatermarkStore
from m16_etl_patterns.cdc_simulation import (
    CDCLog,
    LogBasedCDC,
    CDCConsumer,
)
from m16_etl_patterns.scd_type2 import SCDType2Table


def demo_dag() -> None:
    print("=" * 60)
    print("DAG-BASED TASK SCHEDULING")
    print("=" * 60)

    dag = DAG("ride_analytics_pipeline")
    dag.add_task(Task("extract_rides", execute_fn=lambda: "Extracted 1000 rides"))
    dag.add_task(Task("extract_drivers", execute_fn=lambda: "Extracted 50 drivers"))
    dag.add_task(Task(
        "transform",
        dependencies=["extract_rides", "extract_drivers"],
        execute_fn=lambda: "Transformed data",
    ))
    dag.add_task(Task(
        "load_warehouse",
        dependencies=["transform"],
        execute_fn=lambda: "Loaded to warehouse",
    ))
    dag.add_task(Task(
        "update_dashboards",
        dependencies=["load_warehouse"],
        execute_fn=lambda: "Dashboards updated",
    ))

    print(f"\nTopological order: {dag.topological_sort()}")
    print(f"Parallel groups: {dag.parallel_groups()}")

    print("\nExecution:")
    for result in dag.execute():
        print(f"  [{result.execution_order}] {result.task_name}: {result.status.value} -> {result.output}")


def demo_incremental() -> None:
    print("\n" + "=" * 60)
    print("INCREMENTAL LOADING")
    print("=" * 60)

    store = WatermarkStore()
    loader = IncrementalLoader(store, watermark_column="updated_at")
    destination: list[dict] = []

    source = [
        {"id": 1, "zone": "Manhattan", "updated_at": "2024-01-01T10:00:00"},
        {"id": 2, "zone": "Brooklyn", "updated_at": "2024-01-01T11:00:00"},
        {"id": 3, "zone": "Queens", "updated_at": "2024-01-01T12:00:00"},
    ]

    result = loader.load("rides", source, destination)
    print(f"\nRun 1 (full load): {result.records_loaded} records, watermark: {result.new_watermark}")

    # Add new records to source
    source.append({"id": 4, "zone": "Bronx", "updated_at": "2024-01-02T09:00:00"})

    result = loader.load("rides", source, destination)
    print(f"Run 2 (incremental): {result.records_loaded} records, watermark: {result.new_watermark}")
    print(f"Total in destination: {len(destination)}")


def demo_cdc() -> None:
    print("\n" + "=" * 60)
    print("CHANGE DATA CAPTURE")
    print("=" * 60)

    log = CDCLog()
    log.record_insert("drivers", "d1", {"name": "Alice", "vehicle": "sedan"})
    log.record_insert("drivers", "d2", {"name": "Bob", "vehicle": "suv"})
    log.record_update(
        "drivers", "d1",
        before={"name": "Alice", "vehicle": "sedan"},
        after={"name": "Alice", "vehicle": "luxury"},
    )
    log.record_delete("drivers", "d2", {"name": "Bob", "vehicle": "suv"})

    cdc = LogBasedCDC(log)
    consumer = CDCConsumer()

    events = cdc.poll()
    consumer.apply(events)

    print(f"\nApplied {len(events)} CDC events")
    print(f"Target state: {consumer.target_data}")
    print(f"Stats: {consumer.stats}")


def demo_scd_type2() -> None:
    print("\n" + "=" * 60)
    print("SCD TYPE 2")
    print("=" * 60)

    table = SCDType2Table("drivers")
    table.insert("d1", {"name": "Alice", "vehicle": "sedan", "rating": 4.8},
                 timestamp="2024-01-01T00:00:00")
    table.apply_change("d1", {"vehicle": "luxury", "rating": 4.9},
                       timestamp="2024-06-01T00:00:00")

    print(f"\nCurrent version:")
    current = table.lookup("d1")
    print(f"  {current.to_dict()}")

    print(f"\nAs of 2024-03-01 (before change):")
    past = table.as_of("d1", "2024-03-01T00:00:00")
    print(f"  {past.to_dict()}")

    print(f"\nFull history:")
    for record in table.history("d1"):
        print(f"  v{record.version}: {record.attributes} "
              f"[{record.valid_from} - {record.valid_to or 'current'}]")


if __name__ == "__main__":
    demo_dag()
    demo_incremental()
    demo_cdc()
    demo_scd_type2()
