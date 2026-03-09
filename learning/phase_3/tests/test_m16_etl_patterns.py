"""Tests for Module 16: ETL/ELT Pipeline Patterns."""

import pytest

from learning.phase_3.src.m16_etl_patterns.dag_scheduler import (
    DAG,
    Task,
    TaskStatus,
)
from learning.phase_3.src.m16_etl_patterns.incremental_load import (
    IncrementalLoader,
    WatermarkStore,
)
from learning.phase_3.src.m16_etl_patterns.cdc_simulation import (
    CDCLog,
    CDCOperation,
    LogBasedCDC,
    QueryBasedCDC,
    CDCConsumer,
)
from learning.phase_3.src.m16_etl_patterns.scd_type2 import (
    SCDType2Table,
)


# ── DAG Scheduler ──


class TestDAG:
    def test_topological_sort_respects_dependencies(self):
        dag = DAG("test")
        dag.add_task(Task("extract"))
        dag.add_task(Task("transform", dependencies=["extract"]))
        dag.add_task(Task("load", dependencies=["transform"]))
        order = dag.topological_sort()
        assert order.index("extract") < order.index("transform")
        assert order.index("transform") < order.index("load")

    def test_detect_cycle(self):
        dag = DAG("test")
        dag.add_task(Task("a", dependencies=["c"]))
        dag.add_task(Task("b", dependencies=["a"]))
        dag.add_task(Task("c", dependencies=["b"]))
        cycle = dag.detect_cycles()
        assert cycle is not None

    def test_no_cycle(self):
        dag = DAG("test")
        dag.add_task(Task("a"))
        dag.add_task(Task("b", dependencies=["a"]))
        assert dag.detect_cycles() is None

    def test_topological_sort_with_cycle_raises(self):
        dag = DAG("test")
        dag.add_task(Task("a", dependencies=["b"]))
        dag.add_task(Task("b", dependencies=["a"]))
        with pytest.raises(ValueError, match="cycle"):
            dag.topological_sort()

    def test_execute_runs_in_order(self):
        execution_order = []
        dag = DAG("test")
        dag.add_task(Task("a", execute_fn=lambda: execution_order.append("a")))
        dag.add_task(Task("b", dependencies=["a"],
                          execute_fn=lambda: execution_order.append("b")))
        dag.execute()
        assert execution_order == ["a", "b"]

    def test_failed_task_skips_dependents(self):
        dag = DAG("test")
        dag.add_task(Task("fail", execute_fn=lambda: (_ for _ in ()).throw(RuntimeError("boom"))))
        dag.add_task(Task("downstream", dependencies=["fail"]))
        results = dag.execute()
        fail_result = [r for r in results if r.task_name == "fail"][0]
        downstream_result = [r for r in results if r.task_name == "downstream"][0]
        assert fail_result.status == TaskStatus.FAILED
        assert downstream_result.status == TaskStatus.SKIPPED

    def test_parallel_groups(self):
        dag = DAG("test")
        dag.add_task(Task("extract_a"))
        dag.add_task(Task("extract_b"))
        dag.add_task(Task("transform", dependencies=["extract_a", "extract_b"]))
        groups = dag.parallel_groups()
        assert len(groups) == 2
        assert set(groups[0]) == {"extract_a", "extract_b"}
        assert groups[1] == ["transform"]

    def test_duplicate_task_raises(self):
        dag = DAG("test")
        dag.add_task(Task("a"))
        with pytest.raises(ValueError, match="already exists"):
            dag.add_task(Task("a"))


# ── Incremental Load ──


class TestIncrementalLoad:
    def test_first_run_is_full_load(self):
        store = WatermarkStore()
        loader = IncrementalLoader(store, watermark_column="ts")
        dest: list[dict] = []
        source = [
            {"id": 1, "ts": "2024-01-01"},
            {"id": 2, "ts": "2024-01-02"},
        ]
        result = loader.load("src", source, dest)
        assert result.is_full_load is True
        assert result.records_loaded == 2

    def test_second_run_is_incremental(self):
        store = WatermarkStore()
        loader = IncrementalLoader(store, watermark_column="ts")
        dest: list[dict] = []
        source = [
            {"id": 1, "ts": "2024-01-01"},
            {"id": 2, "ts": "2024-01-02"},
        ]
        loader.load("src", source, dest)
        source.append({"id": 3, "ts": "2024-01-03"})
        result = loader.load("src", source, dest)
        assert result.is_full_load is False
        assert result.records_loaded == 1
        assert len(dest) == 3

    def test_watermark_not_advanced_on_failure(self):
        store = WatermarkStore()
        loader = IncrementalLoader(store, watermark_column="ts")
        source = [{"id": 1, "ts": "2024-01-01"}]
        dest: list[dict] = []
        loader.load("src", source, dest)
        old_wm = store.get("src")
        source.append({"id": 2, "ts": "2024-01-02"})
        result = loader.load_with_failure_handling("src", source, dest, simulate_failure=True)
        assert result.records_loaded == 0
        assert store.get("src") == old_wm

    def test_no_new_records_returns_zero(self):
        store = WatermarkStore()
        loader = IncrementalLoader(store, watermark_column="ts")
        dest: list[dict] = []
        source = [{"id": 1, "ts": "2024-01-01"}]
        loader.load("src", source, dest)
        result = loader.load("src", source, dest)
        assert result.records_loaded == 0


# ── CDC ──


class TestCDC:
    def test_cdc_log_records_operations(self):
        log = CDCLog()
        log.record_insert("t", "k1", {"val": "a"})
        log.record_update("t", "k1", {"val": "a"}, {"val": "b"})
        log.record_delete("t", "k1", {"val": "b"})
        assert log.size == 3

    def test_log_based_cdc_polls_new_events(self):
        log = CDCLog()
        log.record_insert("t", "k1", {"val": "a"})
        cdc = LogBasedCDC(log)
        events = cdc.poll()
        assert len(events) == 1
        log.record_insert("t", "k2", {"val": "b"})
        events = cdc.poll()
        assert len(events) == 1  # Only the new one

    def test_cdc_consumer_applies_insert(self):
        log = CDCLog()
        log.record_insert("t", "k1", {"val": "a"})
        consumer = CDCConsumer()
        consumer.apply(log.events)
        assert consumer.target_count == 1
        assert consumer.target_data["k1"]["val"] == "a"

    def test_cdc_consumer_applies_update(self):
        log = CDCLog()
        log.record_insert("t", "k1", {"val": "a"})
        log.record_update("t", "k1", {"val": "a"}, {"val": "b"})
        consumer = CDCConsumer()
        consumer.apply(log.events)
        assert consumer.target_data["k1"]["val"] == "b"

    def test_cdc_consumer_applies_delete(self):
        log = CDCLog()
        log.record_insert("t", "k1", {"val": "a"})
        log.record_delete("t", "k1", {"val": "a"})
        consumer = CDCConsumer()
        consumer.apply(log.events)
        assert consumer.target_count == 0

    def test_cdc_consumer_stats(self):
        log = CDCLog()
        log.record_insert("t", "k1", {"val": "a"})
        log.record_update("t", "k1", {"val": "a"}, {"val": "b"})
        log.record_delete("t", "k1", {"val": "b"})
        consumer = CDCConsumer()
        consumer.apply(log.events)
        stats = consumer.stats
        assert stats["inserts"] == 1
        assert stats["updates"] == 1
        assert stats["deletes"] == 1


# ── SCD Type 2 ──


class TestSCDType2:
    def test_insert_and_lookup(self):
        table = SCDType2Table("drivers")
        table.insert("d1", {"name": "Alice", "vehicle": "sedan"})
        record = table.lookup("d1")
        assert record is not None
        assert record.attributes["name"] == "Alice"
        assert record.is_current is True

    def test_apply_change_creates_new_version(self):
        table = SCDType2Table("drivers")
        table.insert("d1", {"name": "Alice", "vehicle": "sedan"}, timestamp="2024-01-01T00:00:00")
        closed, new = table.apply_change("d1", {"vehicle": "luxury"}, timestamp="2024-06-01T00:00:00")
        assert closed.is_current is False
        assert closed.valid_to == "2024-06-01T00:00:00"
        assert new.is_current is True
        assert new.version == 2
        assert new.attributes["vehicle"] == "luxury"

    def test_as_of_returns_correct_version(self):
        table = SCDType2Table("drivers")
        table.insert("d1", {"vehicle": "sedan"}, timestamp="2024-01-01T00:00:00")
        table.apply_change("d1", {"vehicle": "luxury"}, timestamp="2024-06-01T00:00:00")

        before = table.as_of("d1", "2024-03-01T00:00:00")
        assert before.attributes["vehicle"] == "sedan"

        after = table.as_of("d1", "2024-09-01T00:00:00")
        assert after.attributes["vehicle"] == "luxury"

    def test_history_returns_all_versions(self):
        table = SCDType2Table("drivers")
        table.insert("d1", {"vehicle": "sedan"}, timestamp="2024-01-01T00:00:00")
        table.apply_change("d1", {"vehicle": "suv"}, timestamp="2024-03-01T00:00:00")
        table.apply_change("d1", {"vehicle": "luxury"}, timestamp="2024-06-01T00:00:00")
        history = table.history("d1")
        assert len(history) == 3
        assert history[0].version == 1
        assert history[2].version == 3

    def test_insert_duplicate_raises(self):
        table = SCDType2Table("drivers")
        table.insert("d1", {"name": "Alice"})
        with pytest.raises(ValueError, match="already exists"):
            table.insert("d1", {"name": "Bob"})
