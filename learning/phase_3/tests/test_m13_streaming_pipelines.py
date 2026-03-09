"""Tests for Module 13: Streaming Pipelines."""

import pytest

from learning.phase_3.src.m13_streaming_pipelines.consumer_groups import (
    PartitionAssigner,
    ConsumerGroup,
    compute_lag,
)
from learning.phase_3.src.m13_streaming_pipelines.windowing import (
    TumblingWindow,
    SlidingWindow,
    SessionWindow,
    WindowResult,
)
from learning.phase_3.src.m13_streaming_pipelines.exactly_once import (
    IdempotentProducer,
    BrokerLog,
    TransactionalWriter,
    DedupProcessor,
    Message,
)


# ── Consumer Groups ──


class TestPartitionAssignment:
    def test_range_assign_even_distribution(self):
        result = PartitionAssigner.range_assign([0, 1, 2, 3, 4, 5], ["C0", "C1", "C2"])
        assert result.total_partitions == 6
        assert len(result.assignments["C0"]) == 2
        assert len(result.assignments["C1"]) == 2
        assert len(result.assignments["C2"]) == 2

    def test_range_assign_uneven_extras_go_to_first(self):
        result = PartitionAssigner.range_assign(list(range(7)), ["C0", "C1", "C2"])
        assert len(result.assignments["C0"]) == 3  # Gets the extra partition
        assert len(result.assignments["C1"]) == 2
        assert len(result.assignments["C2"]) == 2

    def test_round_robin_assign(self):
        result = PartitionAssigner.round_robin_assign(list(range(7)), ["C0", "C1", "C2"])
        assert result.assignments["C0"] == [0, 3, 6]
        assert result.assignments["C1"] == [1, 4]
        assert result.assignments["C2"] == [2, 5]

    def test_assign_empty_consumers(self):
        result = PartitionAssigner.range_assign([0, 1, 2], [])
        assert result.total_partitions == 0

    def test_consumer_for_partition(self):
        result = PartitionAssigner.round_robin_assign([0, 1, 2, 3], ["C0", "C1"])
        assert result.consumer_for_partition(0) == "C0"
        assert result.consumer_for_partition(1) == "C1"
        assert result.consumer_for_partition(99) is None


class TestConsumerGroup:
    def test_join_triggers_rebalance(self):
        group = ConsumerGroup("test", num_partitions=4)
        group.join("C0")
        assert group.rebalance_count == 1
        group.join("C1")
        assert group.rebalance_count == 2

    def test_leave_triggers_rebalance(self):
        group = ConsumerGroup("test", num_partitions=4)
        group.join("C0")
        group.join("C1")
        group.leave("C0")
        assert group.rebalance_count == 3
        assert group.consumers == ["C1"]

    def test_all_partitions_assigned_after_rebalance(self):
        group = ConsumerGroup("test", num_partitions=6)
        group.join("C0")
        group.join("C1")
        result = group.join("C2")
        assert result.total_partitions == 6

    def test_duplicate_join_raises(self):
        group = ConsumerGroup("test", num_partitions=4)
        group.join("C0")
        with pytest.raises(ValueError, match="already in group"):
            group.join("C0")

    def test_leave_nonexistent_raises(self):
        group = ConsumerGroup("test", num_partitions=4)
        with pytest.raises(ValueError, match="not in group"):
            group.leave("C0")


class TestComputeLag:
    def test_lag_positive(self):
        assert compute_lag(1000, 950) == 50

    def test_lag_zero_when_caught_up(self):
        assert compute_lag(100, 100) == 0

    def test_lag_never_negative(self):
        assert compute_lag(50, 100) == 0

    def test_negative_offset_raises(self):
        with pytest.raises(ValueError):
            compute_lag(100, -1)


# ── Windowing ──


class TestTumblingWindow:
    def test_window_boundaries(self):
        tw = TumblingWindow(size_seconds=10)
        tw.add(3, 1.0)
        tw.add(7, 2.0)
        tw.add(12, 3.0)  # Closes [0, 10)
        closed = tw.get_closed_windows()
        assert len(closed) == 1
        assert closed[0].start == 0
        assert closed[0].end == 10
        assert closed[0].count == 2
        assert closed[0].total == 3.0

    def test_flush_returns_all_windows(self):
        tw = TumblingWindow(size_seconds=10)
        tw.add(3, 1.0)
        tw.add(15, 2.0)
        results = tw.flush()
        assert len(results) == 2

    def test_avg_calculation(self):
        tw = TumblingWindow(size_seconds=10)
        tw.add(1, 10.0)
        tw.add(2, 20.0)
        results = tw.flush()
        assert results[0].avg == 15.0


class TestSlidingWindow:
    def test_overlapping_windows(self):
        sw = SlidingWindow(size_seconds=10, slide_seconds=5)
        for i in range(20):
            sw.add(float(i), 1.0)
        results = sw.flush()
        # With overlapping windows, events belong to multiple windows
        assert len(results) > 2

    def test_slide_cannot_exceed_size(self):
        with pytest.raises(ValueError, match="cannot exceed"):
            SlidingWindow(size_seconds=5, slide_seconds=10)


class TestSessionWindow:
    def test_session_gap_closes_window(self):
        sw = SessionWindow(gap_seconds=5)
        sw.add(1, 10)
        sw.add(3, 20)
        sw.add(4, 30)
        # Gap of 8 seconds
        sw.add(12, 40)
        closed = sw.get_closed_windows()
        assert len(closed) == 1
        assert closed[0].count == 3

    def test_flush_closes_active_session(self):
        sw = SessionWindow(gap_seconds=5)
        sw.add(1, 10)
        sw.add(3, 20)
        results = sw.flush()
        assert len(results) == 1
        assert results[0].count == 2

    def test_multiple_sessions(self):
        sw = SessionWindow(gap_seconds=3)
        sw.add(1, 10)
        sw.add(2, 20)
        sw.add(10, 30)
        sw.add(11, 40)
        sw.add(20, 50)
        results = sw.flush()
        assert len(results) == 3


# ── Exactly-Once ──


class TestIdempotentProducer:
    def test_sequence_numbers_increment(self):
        producer = IdempotentProducer("p1")
        msg1 = producer.produce("k1", "v1")
        msg2 = producer.produce("k2", "v2")
        assert msg1.sequence_number == 0
        assert msg2.sequence_number == 1

    def test_broker_dedup_rejects_duplicate(self):
        producer = IdempotentProducer("p1")
        broker = BrokerLog()
        msg = producer.produce("k1", "v1")
        assert broker.append(msg) is True
        retry = producer.retry(msg)
        assert broker.append(retry) is False
        assert broker.size == 1


class TestTransactionalWriter:
    def test_commit_makes_messages_visible(self):
        writer = TransactionalWriter("tx1")
        writer.begin_transaction()
        writer.write(Message("m1", "k1", "v1"))
        writer.write(Message("m2", "k2", "v2"))
        count = writer.commit()
        assert count == 2
        assert len(writer.committed_messages) == 2

    def test_abort_discards_messages(self):
        writer = TransactionalWriter("tx1")
        writer.begin_transaction()
        writer.write(Message("m1", "k1", "v1"))
        discarded = writer.abort()
        assert discarded == 1
        assert len(writer.committed_messages) == 0

    def test_write_without_transaction_raises(self):
        writer = TransactionalWriter("tx1")
        with pytest.raises(RuntimeError, match="No active transaction"):
            writer.write(Message("m1", "k1", "v1"))


class TestDedupProcessor:
    def test_dedup_detects_duplicates(self):
        dedup = DedupProcessor(window_size=100)
        msg = Message("e1", "k1", "v1")
        assert dedup.process(msg) is True
        assert dedup.process(msg) is False
        assert dedup.duplicate_count == 1

    def test_window_eviction(self):
        dedup = DedupProcessor(window_size=3)
        dedup.process(Message("e1", "k1", "v1"))
        dedup.process(Message("e2", "k2", "v2"))
        dedup.process(Message("e3", "k3", "v3"))
        dedup.process(Message("e4", "k4", "v4"))
        # e1 should have been evicted
        assert dedup.seen_count == 3
        assert dedup.process(Message("e1", "k1", "v1-again")) is True
