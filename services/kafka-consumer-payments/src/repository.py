"""
Kafka Consumer Payments repository — dual-write to MinIO Bronze + ClickHouse fact_payments.
"""

import json
import time
from datetime import datetime, timezone
from typing import Optional

from models import PaymentEvent, PaymentFact, ProcessingStats


class PaymentProcessorRepository:
    """Dual-write repository: archives to MinIO Bronze and writes to ClickHouse."""

    def __init__(self, bucket: str = "bronze", prefix: str = "kafka/payment.events.v1"):
        self.bucket = bucket
        self.prefix = prefix

        # In-memory storage
        self.payment_facts: list[PaymentFact] = []
        self.archived_raw: list[dict] = []
        self.stats = ProcessingStats()
        self._start_time = time.time()
        self._archive_count = 0

    def transform_payment_event(self, event: PaymentEvent) -> PaymentFact:
        """Transform a raw payment event into a fact record."""
        payment_at = datetime.fromisoformat(event.timestamp)
        total_amount = round(event.amount + event.tip_amount, 2)

        return PaymentFact(
            payment_id=event.payment_id,
            ride_id=event.ride_id,
            rider_id=event.rider_id,
            driver_id=event.driver_id,
            amount=event.amount,
            tip_amount=event.tip_amount,
            total_amount=total_amount,
            payment_method=event.payment_method,
            currency=event.currency,
            status=event.status,
            processor=event.processor,
            payment_at=payment_at,
            processed_at=datetime.now(timezone.utc),
        )

    def process_batch(self, events: list[dict]) -> tuple[list[PaymentFact], int]:
        """
        Process a batch of payment events with dual write.
        Returns (results, failed_count).
        """
        results: list[PaymentFact] = []
        failed = 0

        for raw in events:
            try:
                event = PaymentEvent(**raw)
                fact = self.transform_payment_event(event)

                # Write to ClickHouse (simulated)
                self.payment_facts.append(fact)
                self.stats.clickhouse_writes += 1

                # Archive to MinIO (simulated)
                self.archived_raw.append(raw)
                self.stats.minio_writes += 1

                results.append(fact)
                self.stats.events_processed += 1
                self.stats.total_amount_processed += fact.total_amount
            except Exception:
                failed += 1
                self.stats.events_failed += 1

        if results:
            self.stats.last_processed_at = datetime.now(timezone.utc).isoformat()
            self._archive_count += 1

        return results, failed

    def get_stats(self) -> ProcessingStats:
        """Return current processing statistics."""
        self.stats.uptime_seconds = round(time.time() - self._start_time, 2)
        return self.stats

    def reset(self):
        """Reset all state."""
        self.payment_facts.clear()
        self.archived_raw.clear()
        self.stats = ProcessingStats()
        self._start_time = time.time()
        self._archive_count = 0
