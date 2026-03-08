"""Tests for Module 08: Event-Driven Architecture."""

import pytest

from learning.phase_2.src.m08_event_driven.event_bus import (
    EventBus,
    DomainEvent,
)
from learning.phase_2.src.m08_event_driven.saga import (
    SagaOrchestrator,
    SagaStatus,
    build_ride_booking_saga,
)
from learning.phase_2.src.m08_event_driven.event_sourcing import (
    EventSourcedTrip,
    TripEventType,
    TripStatus,
)


class TestEventBus:
    def test_publish_delivers_to_subscriber(self):
        bus = EventBus()
        received = []
        bus.subscribe("TestEvent", lambda e: received.append(e.event_type))
        bus.publish(DomainEvent(event_type="TestEvent", aggregate_id="a1"))
        assert received == ["TestEvent"]

    def test_publish_only_matching_type(self):
        bus = EventBus()
        received = []
        bus.subscribe("TypeA", lambda e: received.append(e.event_type))
        bus.publish(DomainEvent(event_type="TypeB", aggregate_id="a1"))
        assert received == []

    def test_wildcard_subscription(self):
        bus = EventBus()
        received = []
        bus.subscribe("*", lambda e: received.append(e.event_type))
        bus.publish(DomainEvent(event_type="TypeA"))
        bus.publish(DomainEvent(event_type="TypeB"))
        assert received == ["TypeA", "TypeB"]

    def test_failing_handler_goes_to_dead_letter(self):
        bus = EventBus()
        bus.subscribe("Fail", lambda e: (_ for _ in ()).throw(RuntimeError("boom")))
        errors = bus.publish(DomainEvent(event_type="Fail"))
        assert len(errors) == 1
        assert len(bus.dead_letter_queue) == 1

    def test_event_store_records_all(self):
        bus = EventBus()
        bus.publish(DomainEvent(event_type="A"))
        bus.publish(DomainEvent(event_type="B"))
        assert len(bus.event_store) == 2

    def test_replay_filters_by_aggregate(self):
        bus = EventBus()
        bus.publish(DomainEvent(event_type="A", aggregate_id="a1"))
        bus.publish(DomainEvent(event_type="A", aggregate_id="a2"))
        replayed = bus.replay(aggregate_id="a1")
        assert len(replayed) == 1

    def test_unsubscribe(self):
        bus = EventBus()
        received = []
        handler = lambda e: received.append(e.event_type)
        bus.subscribe("Test", handler)
        bus.unsubscribe("Test", handler)
        bus.publish(DomainEvent(event_type="Test"))
        assert received == []


class TestSaga:
    def test_successful_saga(self):
        saga = build_ride_booking_saga()
        assert saga.execute({}) is True
        assert saga.status == SagaStatus.COMPLETED

    def test_saga_failure_at_payment(self):
        saga = build_ride_booking_saga(fail_at_step="charge_payment")
        assert saga.execute({}) is False
        assert saga.status == SagaStatus.FAILED

    def test_saga_compensation_runs_in_reverse(self):
        saga = build_ride_booking_saga(fail_at_step="charge_payment")
        saga.execute({})
        compensate_steps = [
            log.step_name for log in saga.log if log.action_type == "compensate"
        ]
        # Should compensate calculate_price, then reserve_driver (reverse order)
        assert compensate_steps == ["calculate_price", "reserve_driver"]

    def test_saga_context_cleaned_on_compensation(self):
        saga = build_ride_booking_saga(fail_at_step="charge_payment")
        ctx = {}
        saga.execute(ctx)
        assert ctx.get("driver_reserved") is False
        assert ctx.get("price_calculated") is False

    def test_saga_failure_at_first_step(self):
        saga = build_ride_booking_saga(fail_at_step="reserve_driver")
        assert saga.execute({}) is False
        assert saga.status == SagaStatus.FAILED


class TestEventSourcing:
    def test_request_trip(self):
        trip = EventSourcedTrip()
        trip.request_trip("t1", "r1", 40.7484, -73.9857, 40.7580, -73.9855)
        assert trip.state.status == TripStatus.REQUESTED
        assert trip.state.trip_id == "t1"

    def test_full_lifecycle(self):
        trip = EventSourcedTrip()
        trip.request_trip("t1", "r1", 40.7484, -73.9857, 40.7580, -73.9855)
        trip.assign_driver("d1")
        trip.start_trip()
        trip.complete_trip(15.50)
        assert trip.state.status == TripStatus.COMPLETED
        assert trip.state.fare_amount == 15.50

    def test_rebuild_from_events(self):
        trip = EventSourcedTrip()
        trip.request_trip("t1", "r1", 40.7484, -73.9857, 40.7580, -73.9855)
        trip.assign_driver("d1")
        trip.start_trip()
        trip.add_waypoint(40.75, -73.98)
        trip.complete_trip(15.50)

        rebuilt = EventSourcedTrip.from_events(trip.events)
        assert rebuilt.state.status == trip.state.status
        assert rebuilt.state.fare_amount == trip.state.fare_amount
        assert rebuilt.state.driver_id == trip.state.driver_id
        assert len(rebuilt.state.waypoints) == len(trip.state.waypoints)

    def test_cannot_assign_driver_twice(self):
        trip = EventSourcedTrip()
        trip.request_trip("t1", "r1", 40.7484, -73.9857, 40.7580, -73.9855)
        trip.assign_driver("d1")
        with pytest.raises(ValueError):
            trip.assign_driver("d2")

    def test_cancel_trip(self):
        trip = EventSourcedTrip()
        trip.request_trip("t1", "r1", 40.7484, -73.9857, 40.7580, -73.9855)
        trip.cancel_trip("changed mind")
        assert trip.state.status == TripStatus.CANCELLED
        assert trip.state.cancellation_reason == "changed mind"

    def test_event_count(self):
        trip = EventSourcedTrip()
        trip.request_trip("t1", "r1", 40.7484, -73.9857, 40.7580, -73.9855)
        trip.assign_driver("d1")
        trip.start_trip()
        trip.complete_trip(10.0)
        assert len(trip.events) == 4
        assert trip.version == 4
