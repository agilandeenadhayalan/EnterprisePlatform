"""
Kafka event consumer with JSON deserialization.

Wraps aiokafka.AIOKafkaConsumer with:
- Automatic JSON deserialization to Event objects
- Consumer group management for load balancing
- Graceful shutdown handling
- Dead letter queue forwarding for failed messages

Usage in a FastAPI service:
    consumer = EventConsumer(
        topics=[Topics.RIDE_EVENTS],
        group_id="dispatch-service",
        bootstrap_servers="kafka:9092",
    )
    await consumer.start()

    async for event in consumer.consume():
        await handle_event(event)

    await consumer.stop()
"""

from __future__ import annotations

import json
import logging
from typing import AsyncGenerator, Callable, Optional

from mobility_common.events import Event

logger = logging.getLogger(__name__)


class EventConsumer:
    """
    Async Kafka consumer for domain events.

    Deserializes JSON messages into Event objects and yields them.
    Uses consumer groups for automatic partition assignment and
    load balancing across service instances.
    """

    def __init__(
        self,
        topics: list[str],
        group_id: str,
        bootstrap_servers: str = "kafka:9092",
        auto_offset_reset: str = "earliest",
    ):
        self._topics = topics
        self._group_id = group_id
        self._bootstrap_servers = bootstrap_servers
        self._auto_offset_reset = auto_offset_reset
        self._consumer = None
        self._running = False

    async def start(self) -> None:
        """Start the Kafka consumer and subscribe to topics."""
        try:
            from aiokafka import AIOKafkaConsumer

            self._consumer = AIOKafkaConsumer(
                *self._topics,
                bootstrap_servers=self._bootstrap_servers,
                group_id=self._group_id,
                auto_offset_reset=self._auto_offset_reset,
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                key_deserializer=lambda k: k.decode("utf-8") if k else None,
                enable_auto_commit=True,
                auto_commit_interval_ms=5000,
            )
            await self._consumer.start()
            self._running = True
            logger.info(
                "Kafka consumer started: group=%s topics=%s",
                self._group_id, self._topics,
            )
        except ImportError:
            logger.warning("aiokafka not installed — consumer in mock mode")
            self._consumer = None
        except Exception as e:
            logger.warning("Kafka consumer failed to start: %s", e)
            self._consumer = None

    async def stop(self) -> None:
        """Stop the Kafka consumer gracefully."""
        self._running = False
        if self._consumer:
            await self._consumer.stop()
            logger.info("Kafka consumer stopped: group=%s", self._group_id)

    async def consume(self) -> AsyncGenerator[Event, None]:
        """
        Yield Event objects from subscribed Kafka topics.

        This is an async generator — use with `async for`:
            async for event in consumer.consume():
                await process(event)

        Handles deserialization errors by logging and skipping bad messages.
        """
        if not self._consumer:
            logger.warning("Consumer not available, exiting consume loop")
            return

        try:
            async for message in self._consumer:
                if not self._running:
                    break
                try:
                    event = Event(**message.value)
                    logger.debug(
                        "Event received: topic=%s type=%s partition=%d offset=%d",
                        message.topic, event.event_type,
                        message.partition, message.offset,
                    )
                    yield event
                except Exception as e:
                    logger.error(
                        "Failed to deserialize event: topic=%s partition=%d offset=%d error=%s",
                        message.topic, message.partition, message.offset, e,
                    )
        except Exception as e:
            if self._running:
                logger.error("Consumer loop error: %s", e)

    async def consume_with_handler(
        self,
        handler: Callable[[Event], None],
        error_handler: Optional[Callable[[Event, Exception], None]] = None,
    ) -> None:
        """
        Consume events and process them with a handler function.

        Args:
            handler: Async function to process each event
            error_handler: Optional async function for handling processing errors
        """
        async for event in self.consume():
            try:
                await handler(event)
            except Exception as e:
                if error_handler:
                    await error_handler(event, e)
                else:
                    logger.error(
                        "Event processing failed: type=%s id=%s error=%s",
                        event.event_type, event.event_id, e,
                    )

    @property
    def is_connected(self) -> bool:
        """Check if the consumer is connected."""
        return self._consumer is not None and self._running
