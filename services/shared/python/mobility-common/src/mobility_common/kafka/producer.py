"""
Kafka event producer with JSON serialization.

Wraps aiokafka.AIOKafkaProducer with:
- Automatic JSON serialization of Event objects
- Partition key extraction from correlation_id
- Connection lifecycle management (start/stop)
- Error handling with retry metadata

Usage in a FastAPI service:
    producer = EventProducer(bootstrap_servers="kafka:9092")
    await producer.start()

    event = Event(
        event_type=EventTypes.RIDE_REQUESTED,
        source="trip-service",
        correlation_id=trip_id,
        payload={"rider_id": "...", "pickup": {...}},
    )
    await producer.send_event(Topics.RIDE_EVENTS, event)

    await producer.stop()
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from mobility_common.events import Event

logger = logging.getLogger(__name__)


class EventProducer:
    """
    Async Kafka producer for domain events.

    Serializes Event objects to JSON and sends them to Kafka topics.
    Uses the event's correlation_id as the partition key to ensure
    related events land in the same partition (ordering guarantee).
    """

    def __init__(
        self,
        bootstrap_servers: str = "kafka:9092",
        client_id: str = "mobility-producer",
    ):
        self._bootstrap_servers = bootstrap_servers
        self._client_id = client_id
        self._producer = None

    async def start(self) -> None:
        """Start the Kafka producer connection."""
        try:
            from aiokafka import AIOKafkaProducer

            self._producer = AIOKafkaProducer(
                bootstrap_servers=self._bootstrap_servers,
                client_id=self._client_id,
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks="all",  # Wait for all replicas to acknowledge
                retry_backoff_ms=100,
                request_timeout_ms=30000,
            )
            await self._producer.start()
            logger.info("Kafka producer started: %s", self._bootstrap_servers)
        except ImportError:
            logger.warning("aiokafka not installed — producer in mock mode")
            self._producer = None
        except Exception as e:
            logger.warning("Kafka producer failed to start: %s", e)
            self._producer = None

    async def stop(self) -> None:
        """Stop the Kafka producer connection."""
        if self._producer:
            await self._producer.stop()
            logger.info("Kafka producer stopped")

    async def send_event(
        self,
        topic: str,
        event: Event,
        key: Optional[str] = None,
    ) -> bool:
        """
        Send a domain event to a Kafka topic.

        Args:
            topic: Kafka topic name (use Topics constants)
            event: Event object to serialize and send
            key: Optional partition key (defaults to event.correlation_id)

        Returns:
            True if sent successfully, False if producer unavailable
        """
        if not self._producer:
            logger.debug("Producer not available, event not sent: %s", event.event_type)
            return False

        partition_key = key or event.to_kafka_key()
        payload = event.model_dump(mode="json")

        try:
            await self._producer.send_and_wait(
                topic=topic,
                value=payload,
                key=partition_key,
            )
            logger.info(
                "Event sent: topic=%s type=%s id=%s",
                topic, event.event_type, event.event_id,
            )
            return True
        except Exception as e:
            logger.error(
                "Failed to send event: topic=%s type=%s error=%s",
                topic, event.event_type, e,
            )
            return False

    @property
    def is_connected(self) -> bool:
        """Check if the producer is connected."""
        return self._producer is not None
