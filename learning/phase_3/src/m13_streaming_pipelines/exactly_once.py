"""
Exactly-Once Semantics in Stream Processing
==============================================

Delivery guarantees are one of the hardest problems in distributed systems:

1. **At-most-once** — Fire and forget. Fast, but messages can be lost.
2. **At-least-once** — Retry until acknowledged. No loss, but duplicates.
3. **Exactly-once** — Each message processed exactly once. The holy grail.

True exactly-once is achieved by combining:
    at-least-once delivery + idempotent processing = exactly-once semantics

THREE PATTERNS DEMONSTRATED HERE:

1. **IdempotentProducer** — Uses sequence numbers to prevent duplicate writes.
   Kafka's idempotent producer (enable.idempotence=true) does this.
   The broker deduplicates by (producer_id, sequence_number).

2. **TransactionalWriter** — Atomic read-process-write across topics.
   Kafka transactions ensure that consumed offsets and produced records
   are committed or aborted together.

3. **DedupProcessor** — Consumer-side deduplication using event IDs.
   Even with idempotent producers, network retries can cause duplicates.
   A sliding window of seen IDs catches and discards them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from collections import OrderedDict
from enum import Enum
from typing import Any


@dataclass(frozen=True)
class Message:
    """A stream message with an ID, key, value, and optional sequence number."""
    message_id: str
    key: str
    value: Any
    sequence_number: int = 0


class IdempotentProducer:
    """
    Simulates Kafka's idempotent producer.

    Each message is assigned a monotonically increasing sequence number.
    If the same sequence number is sent twice (e.g., due to retry),
    the broker detects the duplicate and ignores it.

    HOW IT WORKS IN KAFKA:
    - Producer gets a unique producer_id from the broker.
    - Each message gets (producer_id, partition, sequence_number).
    - Broker checks: if sequence_number <= last seen, it's a duplicate.
    - This is transparent to application code when enabled.
    """

    def __init__(self, producer_id: str) -> None:
        self.producer_id = producer_id
        self._sequence = 0
        self._sent: list[Message] = []

    @property
    def next_sequence(self) -> int:
        return self._sequence

    def produce(self, key: str, value: Any) -> Message:
        """
        Produce a message with the next sequence number.
        Returns the message that was produced.
        """
        msg = Message(
            message_id=f"{self.producer_id}-{self._sequence}",
            key=key,
            value=value,
            sequence_number=self._sequence,
        )
        self._sequence += 1
        self._sent.append(msg)
        return msg

    def retry(self, message: Message) -> Message:
        """
        Retry sending a message (same sequence number).
        In Kafka, the broker would detect this as a duplicate.
        """
        return Message(
            message_id=message.message_id,
            key=message.key,
            value=message.value,
            sequence_number=message.sequence_number,
        )

    @property
    def sent_messages(self) -> list[Message]:
        return list(self._sent)


class BrokerLog:
    """
    Simulates a broker's commit log with idempotent dedup.

    Keeps track of the last sequence number per producer.
    Rejects duplicate writes with the same sequence number.
    """

    def __init__(self) -> None:
        self._log: list[Message] = []
        self._producer_sequences: dict[str, int] = {}

    def append(self, message: Message) -> bool:
        """
        Append a message to the log.

        Returns True if written, False if duplicate detected.
        """
        producer_id = message.message_id.rsplit("-", 1)[0]
        last_seq = self._producer_sequences.get(producer_id, -1)

        if message.sequence_number <= last_seq:
            # Duplicate detected — idempotent dedup
            return False

        self._producer_sequences[producer_id] = message.sequence_number
        self._log.append(message)
        return True

    @property
    def messages(self) -> list[Message]:
        return list(self._log)

    @property
    def size(self) -> int:
        return len(self._log)


class TransactionState(str, Enum):
    NONE = "none"
    IN_PROGRESS = "in_progress"
    COMMITTED = "committed"
    ABORTED = "aborted"


class TransactionalWriter:
    """
    Simulates Kafka's transactional producer.

    A transaction groups multiple writes (and offset commits) into
    an atomic unit. Either all succeed (commit) or none (abort).

    USE CASE:
    read from input topic -> process -> write to output topic + commit input offset
    All in one atomic transaction. If the consumer crashes mid-processing,
    the transaction is aborted and the input offset is not advanced.

    ISOLATION LEVELS:
    - read_uncommitted: Consumer sees all messages (including uncommitted).
    - read_committed: Consumer only sees committed messages.
    """

    def __init__(self, transactional_id: str) -> None:
        self.transactional_id = transactional_id
        self._state = TransactionState.NONE
        self._pending: list[Message] = []
        self._committed: list[Message] = []
        self._transaction_count = 0

    @property
    def state(self) -> TransactionState:
        return self._state

    @property
    def committed_messages(self) -> list[Message]:
        return list(self._committed)

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    def begin_transaction(self) -> None:
        """Start a new transaction."""
        if self._state == TransactionState.IN_PROGRESS:
            raise RuntimeError("Transaction already in progress")
        self._state = TransactionState.IN_PROGRESS
        self._pending = []
        self._transaction_count += 1

    def write(self, message: Message) -> None:
        """Write a message within the current transaction."""
        if self._state != TransactionState.IN_PROGRESS:
            raise RuntimeError("No active transaction — call begin_transaction() first")
        self._pending.append(message)

    def commit(self) -> int:
        """
        Commit the transaction — all pending writes become visible.
        Returns the number of messages committed.
        """
        if self._state != TransactionState.IN_PROGRESS:
            raise RuntimeError("No active transaction to commit")
        count = len(self._pending)
        self._committed.extend(self._pending)
        self._pending = []
        self._state = TransactionState.COMMITTED
        return count

    def abort(self) -> int:
        """
        Abort the transaction — all pending writes are discarded.
        Returns the number of messages discarded.
        """
        if self._state != TransactionState.IN_PROGRESS:
            raise RuntimeError("No active transaction to abort")
        count = len(self._pending)
        self._pending = []
        self._state = TransactionState.ABORTED
        return count


class DedupProcessor:
    """
    Consumer-side deduplication using a sliding window of seen event IDs.

    Even with idempotent producers, consumer retries can process
    the same message twice (e.g., crash after processing but before
    committing the offset). A dedup window catches these.

    HOW IT WORKS:
    - Maintain a set of recently seen message IDs.
    - Before processing, check if the ID was already seen.
    - If seen, skip it (idempotent).
    - If not seen, process it and add the ID to the set.
    - Evict old IDs to bound memory (sliding window).
    """

    def __init__(self, window_size: int = 1000) -> None:
        if window_size <= 0:
            raise ValueError("Window size must be positive")
        self.window_size = window_size
        self._seen: OrderedDict[str, None] = OrderedDict()
        self._processed: list[Message] = []
        self._duplicate_count = 0

    def process(self, message: Message) -> bool:
        """
        Process a message if not a duplicate.

        Returns True if processed, False if duplicate detected.
        """
        if message.message_id in self._seen:
            self._duplicate_count += 1
            return False

        # Add to seen set
        self._seen[message.message_id] = None

        # Evict oldest if window exceeded
        while len(self._seen) > self.window_size:
            self._seen.popitem(last=False)

        self._processed.append(message)
        return True

    @property
    def processed_messages(self) -> list[Message]:
        return list(self._processed)

    @property
    def processed_count(self) -> int:
        return len(self._processed)

    @property
    def duplicate_count(self) -> int:
        return self._duplicate_count

    @property
    def seen_count(self) -> int:
        return len(self._seen)
