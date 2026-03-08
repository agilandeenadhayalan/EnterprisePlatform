"""Tests for Module 11: Real-Time Communication."""

import pytest

from learning.phase_2.src.m11_realtime_comms.pubsub import (
    PubSubSystem,
    Channel,
    Message,
    _topic_matches,
)
from learning.phase_2.src.m11_realtime_comms.backpressure import (
    BackpressureStrategy,
    simulate_backpressure,
)
from learning.phase_2.src.m11_realtime_comms.presence import (
    PresenceTracker,
    PresenceState,
)


class TestTopicMatching:
    def test_exact_match(self):
        assert _topic_matches("trip.123.location", "trip.123.location") is True

    def test_exact_no_match(self):
        assert _topic_matches("trip.123.location", "trip.456.location") is False

    def test_single_wildcard(self):
        assert _topic_matches("trip.*.location", "trip.123.location") is True

    def test_multi_wildcard(self):
        assert _topic_matches("trip.123.#", "trip.123.location") is True
        assert _topic_matches("trip.123.#", "trip.123.status") is True

    def test_wildcard_no_match_different_segments(self):
        assert _topic_matches("trip.*.location", "trip.123.status") is False


class TestChannel:
    def test_channel_publish_delivers(self):
        ch = Channel("test")
        received = []
        ch.subscribe("s1", lambda m: received.append(m.payload))
        ch.publish({"key": "value"})
        assert len(received) == 1
        assert received[0] == {"key": "value"}

    def test_channel_ordering(self):
        ch = Channel("test")
        sequences = []
        ch.subscribe("s1", lambda m: sequences.append(m.sequence))
        ch.publish({"a": 1})
        ch.publish({"b": 2})
        ch.publish({"c": 3})
        assert sequences == [1, 2, 3]

    def test_unsubscribe(self):
        ch = Channel("test")
        received = []
        ch.subscribe("s1", lambda m: received.append(1))
        ch.unsubscribe("s1")
        ch.publish({"x": 1})
        assert received == []


class TestPubSubSystem:
    def test_topic_publish_subscribe(self):
        ps = PubSubSystem()
        received = []
        ps.subscribe("trip.*.location", "map", lambda m: received.append(m.topic))
        ps.publish("trip.123.location", {"lat": 40.7})
        assert len(received) == 1

    def test_replay(self):
        ps = PubSubSystem()
        ps.publish("a.b", {"x": 1})
        ps.publish("a.c", {"x": 2})
        replayed = ps.replay()
        assert len(replayed) == 2

    def test_replay_with_filter(self):
        ps = PubSubSystem()
        ps.publish("trip.1.loc", {})
        ps.publish("trip.2.loc", {})
        ps.publish("driver.1.status", {})
        replayed = ps.replay(topic_pattern="trip.*.loc")
        assert len(replayed) == 2


class TestBackpressure:
    def test_drop_strategy_loses_messages(self):
        stats = simulate_backpressure(
            BackpressureStrategy.DROP, produce_rate=100, consume_rate=40, ticks=10)
        assert stats.dropped > 0
        assert stats.consumed < stats.produced

    def test_buffer_strategy_grows_buffer(self):
        stats = simulate_backpressure(
            BackpressureStrategy.BUFFER, produce_rate=100, consume_rate=40, ticks=10)
        assert stats.max_buffer_size > 0

    def test_throttle_slows_producer(self):
        stats = simulate_backpressure(
            BackpressureStrategy.THROTTLE, produce_rate=100, consume_rate=40, ticks=20)
        assert stats.producer_throttled_ticks > 0

    def test_balanced_no_issues(self):
        stats = simulate_backpressure(
            BackpressureStrategy.DROP, produce_rate=40, consume_rate=40, ticks=10)
        assert stats.dropped == 0


class TestPresence:
    def test_heartbeat_sets_online(self):
        tracker = PresenceTracker()
        tracker.heartbeat("u1", timestamp=100.0)
        p = tracker.get_presence("u1", now=100.0)
        assert p.state == PresenceState.ONLINE

    def test_away_after_timeout(self):
        tracker = PresenceTracker(away_timeout=30.0, offline_timeout=60.0)
        tracker.heartbeat("u1", timestamp=100.0)
        p = tracker.get_presence("u1", now=140.0)  # 40s elapsed
        assert p.state == PresenceState.AWAY

    def test_offline_after_timeout(self):
        tracker = PresenceTracker(away_timeout=30.0, offline_timeout=60.0)
        tracker.heartbeat("u1", timestamp=100.0)
        p = tracker.get_presence("u1", now=170.0)  # 70s elapsed
        assert p.state == PresenceState.OFFLINE

    def test_count_by_state(self):
        tracker = PresenceTracker(away_timeout=30.0, offline_timeout=60.0)
        tracker.heartbeat("u1", timestamp=100.0)
        tracker.heartbeat("u2", timestamp=100.0)
        tracker.heartbeat("u3", timestamp=50.0)   # 50s ago -> away
        tracker.heartbeat("u4", timestamp=30.0)   # 70s ago -> offline
        counts = tracker.count_by_state(now=100.0)
        assert counts[PresenceState.ONLINE] == 2
        assert counts[PresenceState.AWAY] == 1
        assert counts[PresenceState.OFFLINE] == 1

    def test_unknown_user_is_offline(self):
        tracker = PresenceTracker()
        p = tracker.get_presence("unknown")
        assert p.state == PresenceState.OFFLINE
