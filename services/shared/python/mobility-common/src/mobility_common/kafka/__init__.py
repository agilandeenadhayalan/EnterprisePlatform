"""
Kafka producer/consumer utilities for event-driven architecture.

Provides a standardized way for all services to produce and consume
domain events through Kafka, using the Event envelope from events.py.
"""

from mobility_common.kafka.producer import EventProducer
from mobility_common.kafka.consumer import EventConsumer
from mobility_common.kafka.topics import Topics

__all__ = ["EventProducer", "EventConsumer", "Topics"]
