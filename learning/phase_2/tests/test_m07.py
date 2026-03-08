"""Tests for Module 07: Domain-Driven Design."""

import pytest

from learning.phase_2.src.m07_domain_driven_design.bounded_contexts import (
    UserIdentity,
    UserRole,
    Rider,
    Customer,
    Driver,
    DriverStatus,
    Vehicle,
    PaymentMethod,
    ContextMapper,
)
from learning.phase_2.src.m07_domain_driven_design.aggregates import (
    TripAggregate,
    TripStatus,
    Location,
    FareBreakdown,
    InvalidTransitionError,
    InvalidStateError,
)


class TestBoundedContexts:
    def test_user_identity_has_role(self):
        user = UserIdentity(user_id="u1", email="a@b.com", phone="123",
                            roles=(UserRole.RIDER, UserRole.DRIVER))
        assert user.has_role(UserRole.RIDER) is True
        assert user.has_role(UserRole.ADMIN) is False

    def test_rider_has_defaults(self):
        rider = Rider(rider_id="r1", display_name="Alice")
        assert rider.rating == 5.0
        assert rider.total_trips == 0

    def test_customer_can_pay_with_card(self):
        customer = Customer(customer_id="c1")
        assert customer.can_pay(100.0) is True

    def test_driver_go_online(self):
        vehicle = Vehicle("v1", "standard", "ABC-123")
        driver = Driver(driver_id="d1", display_name="Bob", vehicle=vehicle)
        assert driver.status == DriverStatus.OFFLINE
        driver.go_online()
        assert driver.status == DriverStatus.AVAILABLE

    def test_driver_go_offline_only_from_available(self):
        vehicle = Vehicle("v1", "standard", "ABC-123")
        driver = Driver(driver_id="d1", display_name="Bob", vehicle=vehicle,
                        status=DriverStatus.ON_TRIP)
        driver.go_offline()
        assert driver.status == DriverStatus.ON_TRIP  # No change


class TestContextMapper:
    def test_identity_to_rider(self):
        user = UserIdentity(user_id="u1", email="alice@example.com", phone="123")
        rider = ContextMapper.identity_to_rider(user)
        assert rider.rider_id == "u1"
        assert rider.display_name == "alice"

    def test_identity_to_customer(self):
        user = UserIdentity(user_id="u1", email="alice@example.com", phone="123")
        customer = ContextMapper.identity_to_customer(user)
        assert customer.customer_id == "u1"

    def test_identity_to_driver_requires_driver_role(self):
        user = UserIdentity(user_id="u1", email="a@b.com", phone="123",
                            roles=(UserRole.RIDER,))
        vehicle = Vehicle("v1", "standard", "ABC-123")
        with pytest.raises(ValueError, match="DRIVER role"):
            ContextMapper.identity_to_driver(user, vehicle)

    def test_rider_to_customer_id(self):
        rider = Rider(rider_id="u1", display_name="Alice")
        assert ContextMapper.rider_to_customer_id(rider) == "u1"


class TestTripAggregate:
    def _make_trip(self) -> TripAggregate:
        pickup = Location(lat=40.7484, lon=-73.9857)
        dropoff = Location(lat=40.7580, lon=-73.9855)
        return TripAggregate(trip_id="t1", rider_id="r1",
                             pickup=pickup, dropoff=dropoff)

    def test_trip_requires_pickup_and_dropoff(self):
        pickup = Location(lat=40.7484, lon=-73.9857)
        with pytest.raises(ValueError, match="pickup and dropoff"):
            TripAggregate(trip_id="t1", rider_id="r1",
                          pickup=pickup, dropoff=None)

    def test_trip_starts_as_requested(self):
        trip = self._make_trip()
        assert trip.status == TripStatus.REQUESTED

    def test_assign_driver(self):
        trip = self._make_trip()
        trip.assign_driver("d1")
        assert trip.status == TripStatus.DRIVER_ASSIGNED
        assert trip.driver_id == "d1"

    def test_cannot_start_without_driver(self):
        trip = self._make_trip()
        with pytest.raises(InvalidTransitionError):
            trip.start_trip()

    def test_full_lifecycle(self):
        trip = self._make_trip()
        trip.assign_driver("d1")
        trip.start_trip()
        fare = FareBreakdown(base_fare=2.50, distance_charge=5.00, time_charge=3.00)
        trip.complete_trip(fare)
        assert trip.status == TripStatus.COMPLETED
        assert trip.fare is not None
        assert trip.fare.total == 10.50

    def test_cannot_cancel_completed_trip(self):
        trip = self._make_trip()
        trip.assign_driver("d1")
        trip.start_trip()
        trip.complete_trip(FareBreakdown(base_fare=2.50, distance_charge=5.00, time_charge=3.00))
        with pytest.raises(InvalidTransitionError):
            trip.cancel_trip("changed mind")

    def test_cannot_add_waypoint_before_start(self):
        trip = self._make_trip()
        with pytest.raises(InvalidStateError):
            trip.add_waypoint(Location(lat=40.75, lon=-73.98))

    def test_fare_must_be_positive(self):
        trip = self._make_trip()
        trip.assign_driver("d1")
        trip.start_trip()
        with pytest.raises(ValueError, match="positive"):
            trip.complete_trip(FareBreakdown(base_fare=0, distance_charge=0, time_charge=0))

    def test_invalid_location(self):
        with pytest.raises(ValueError, match="latitude"):
            Location(lat=91, lon=0)

    def test_fare_breakdown_total_with_surge(self):
        fare = FareBreakdown(base_fare=2.50, distance_charge=5.00,
                             time_charge=3.00, surge_multiplier=1.5, tip=2.00)
        expected = round((2.50 + 5.00 + 3.00) * 1.5 + 2.00, 2)
        assert fare.total == expected
