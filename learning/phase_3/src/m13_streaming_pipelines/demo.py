"""
Demo: Streaming Pipelines Concepts
====================================

Runs demonstrations of consumer groups, windowing, and exactly-once semantics.
"""

from m13_streaming_pipelines.consumer_groups import (
    PartitionAssigner,
    ConsumerGroup,
    compute_lag,
)
from m13_streaming_pipelines.windowing import (
    TumblingWindow,
    SlidingWindow,
    SessionWindow,
)
from m13_streaming_pipelines.exactly_once import (
    IdempotentProducer,
    BrokerLog,
    TransactionalWriter,
    DedupProcessor,
    Message,
)


def demo_consumer_groups() -> None:
    print("=" * 60)
    print("CONSUMER GROUPS & PARTITION ASSIGNMENT")
    print("=" * 60)

    partitions = list(range(12))
    consumers = ["C0", "C1", "C2"]

    # Range assignment
    result = PartitionAssigner.range_assign(partitions, consumers)
    print("\nRange Assignment (12 partitions, 3 consumers):")
    for consumer, parts in result.assignments.items():
        print(f"  {consumer} -> {parts}")

    # Round-robin assignment
    result = PartitionAssigner.round_robin_assign(partitions, consumers)
    print("\nRound-Robin Assignment:")
    for consumer, parts in result.assignments.items():
        print(f"  {consumer} -> {parts}")

    # Rebalancing demo
    print("\n--- Rebalancing Demo ---")
    group = ConsumerGroup("trip-processors", num_partitions=6)
    assignment = group.join("C0")
    print(f"After C0 joins: {assignment.assignments}")
    assignment = group.join("C1")
    print(f"After C1 joins: {assignment.assignments}")
    assignment = group.join("C2")
    print(f"After C2 joins: {assignment.assignments}")
    assignment = group.leave("C1")
    print(f"After C1 leaves: {assignment.assignments}")
    print(f"Total rebalances: {group.rebalance_count}")

    # Lag
    print(f"\nLag(current=1000, committed=950) = {compute_lag(1000, 950)}")
    print(f"Lag(current=1000, committed=1000) = {compute_lag(1000, 1000)}")


def demo_windowing() -> None:
    print("\n" + "=" * 60)
    print("WINDOWING STRATEGIES")
    print("=" * 60)

    # Tumbling window
    print("\n--- Tumbling Window (size=10s) ---")
    tw = TumblingWindow(size_seconds=10)
    events = [(1, 5.0), (3, 3.0), (7, 8.0), (12, 4.0), (15, 6.0), (22, 2.0)]
    for ts, val in events:
        tw.add(ts, val)
        print(f"  Added event(t={ts}, v={val})")
    results = tw.flush()
    for r in results:
        print(f"  Window [{r.start}, {r.end}): count={r.count}, sum={r.total}, avg={r.avg:.2f}")

    # Session window
    print("\n--- Session Window (gap=5s) ---")
    sw = SessionWindow(gap_seconds=5)
    events = [(1, 10), (3, 20), (4, 30), (12, 40), (14, 50), (25, 60)]
    for ts, val in events:
        sw.add(ts, val)
        print(f"  Added event(t={ts}, v={val})")
    results = sw.flush()
    for r in results:
        print(f"  Session [{r.start}, {r.end}]: count={r.count}, sum={r.total}")


def demo_exactly_once() -> None:
    print("\n" + "=" * 60)
    print("EXACTLY-ONCE SEMANTICS")
    print("=" * 60)

    # Idempotent producer + broker dedup
    print("\n--- Idempotent Producer ---")
    producer = IdempotentProducer("prod-1")
    broker = BrokerLog()

    msg1 = producer.produce("key-1", "ride-started")
    msg2 = producer.produce("key-2", "ride-completed")

    print(f"  Write msg1: {broker.append(msg1)}")
    print(f"  Write msg2: {broker.append(msg2)}")

    # Simulate retry of msg1
    retry = producer.retry(msg1)
    print(f"  Retry msg1: {broker.append(retry)} (duplicate detected!)")
    print(f"  Broker log size: {broker.size} (only 2, not 3)")

    # Transactional writer
    print("\n--- Transactional Writer ---")
    writer = TransactionalWriter("txn-1")
    writer.begin_transaction()
    writer.write(Message("m1", "k1", "v1"))
    writer.write(Message("m2", "k2", "v2"))
    committed = writer.commit()
    print(f"  Committed {committed} messages")

    writer.begin_transaction()
    writer.write(Message("m3", "k3", "v3"))
    aborted = writer.abort()
    print(f"  Aborted {aborted} messages")
    print(f"  Total committed: {len(writer.committed_messages)}")

    # Dedup processor
    print("\n--- Dedup Processor ---")
    dedup = DedupProcessor(window_size=100)
    messages = [
        Message("e1", "k1", "first"),
        Message("e2", "k2", "second"),
        Message("e1", "k1", "first-retry"),  # duplicate!
        Message("e3", "k3", "third"),
        Message("e2", "k2", "second-retry"),  # duplicate!
    ]
    for msg in messages:
        result = dedup.process(msg)
        status = "processed" if result else "DUPLICATE"
        print(f"  {msg.message_id}: {status}")
    print(f"  Processed: {dedup.processed_count}, Duplicates: {dedup.duplicate_count}")


if __name__ == "__main__":
    demo_consumer_groups()
    demo_windowing()
    demo_exactly_once()
