"""
Bounded Contexts & Context Mapping
====================================

Demonstrates how different subdomains model the same real-world concept
differently. A "User" in the Identity context is NOT the same as a
"Rider" in the Ride context, even though they represent the same person.

WHY bounded contexts:
- Each subdomain has its own ubiquitous language
- Prevents a single bloated "God model" that tries to represent everything
- Teams can evolve their models independently
- Clear ownership boundaries for microservices

Architecture:
    Identity Context ──[ContextMapper]── Ride Context
         |                                    |
    User (auth, roles)              Rider (pickup, preferences)
         |
    ──[ContextMapper]── Payment Context
                              |
                        Customer (billing, wallet)
         |
    ──[ContextMapper]── Driver Context
                              |
                        Driver (vehicle, availability)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ── Identity Context ──
# Concerned with: authentication, authorization, user profile


class UserRole(str, Enum):
    RIDER = "rider"
    DRIVER = "driver"
    ADMIN = "admin"


@dataclass(frozen=True)
class UserIdentity:
    """
    User in the Identity context.

    This context cares about WHO you are: credentials, roles, permissions.
    It does NOT care about ride history or payment methods.
    """
    user_id: str
    email: str
    phone: str
    roles: tuple[UserRole, ...] = (UserRole.RIDER,)
    is_verified: bool = False

    def has_role(self, role: UserRole) -> bool:
        return role in self.roles


# ── Ride Context ──
# Concerned with: trip management, matching, routing


@dataclass
class RidePreferences:
    """Value object for rider preferences within the Ride context."""
    preferred_vehicle_type: str = "standard"
    max_wait_minutes: int = 10
    accessibility_needed: bool = False


@dataclass
class Rider:
    """
    User in the Ride context — called 'Rider' here, not 'User'.

    This context cares about WHAT you want: pickup, dropoff, preferences.
    It does NOT know about your password or billing info.
    """
    rider_id: str           # Same underlying person, different identity
    display_name: str
    rating: float = 5.0
    total_trips: int = 0
    preferences: RidePreferences = field(default_factory=RidePreferences)


# ── Payment Context ──
# Concerned with: billing, wallets, transactions


class PaymentMethod(str, Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    WALLET = "wallet"
    CASH = "cash"


@dataclass
class Customer:
    """
    User in the Payment context — called 'Customer' here.

    This context cares about HOW you pay. It knows nothing about
    ride routes, driver matching, or authentication.
    """
    customer_id: str
    default_payment: PaymentMethod = PaymentMethod.CREDIT_CARD
    wallet_balance: float = 0.0
    payment_methods: list[PaymentMethod] = field(
        default_factory=lambda: [PaymentMethod.CREDIT_CARD]
    )

    def can_pay(self, amount: float) -> bool:
        """Check if customer can cover a charge."""
        if PaymentMethod.WALLET in self.payment_methods:
            return self.wallet_balance >= amount or len(self.payment_methods) > 1
        return len(self.payment_methods) > 0


# ── Driver Context ──
# Concerned with: vehicle, availability, location


class DriverStatus(str, Enum):
    OFFLINE = "offline"
    AVAILABLE = "available"
    ON_TRIP = "on_trip"
    RETURNING = "returning"


@dataclass
class Vehicle:
    """Value object representing a driver's vehicle."""
    vehicle_id: str
    vehicle_type: str       # "standard", "premium", "xl"
    license_plate: str
    capacity: int = 4


@dataclass
class Driver:
    """
    User in the Driver context.

    This context cares about the driver's operational state:
    vehicle, location, availability. It does NOT know about
    the driver's password or payment preferences as a rider.
    """
    driver_id: str
    display_name: str
    vehicle: Vehicle
    status: DriverStatus = DriverStatus.OFFLINE
    rating: float = 5.0
    acceptance_rate: float = 0.95
    current_lat: float = 0.0
    current_lon: float = 0.0

    def go_online(self) -> None:
        if self.status == DriverStatus.OFFLINE:
            self.status = DriverStatus.AVAILABLE

    def go_offline(self) -> None:
        if self.status == DriverStatus.AVAILABLE:
            self.status = DriverStatus.OFFLINE


# ── Context Mapper ──


class ContextMapper:
    """
    Maps entities between bounded contexts.

    WHY: Contexts need to communicate, but they should NOT share models.
    The Context Mapper acts as an Anti-Corruption Layer, translating
    between the languages of different contexts.

    In a real system, this translation happens at service boundaries
    (e.g., API calls, events, shared IDs).
    """

    @staticmethod
    def identity_to_rider(user: UserIdentity) -> Rider:
        """
        Map an Identity context User to a Ride context Rider.

        Only transfers the data the Ride context needs.
        The Ride context doesn't know about passwords or roles.
        """
        return Rider(
            rider_id=user.user_id,
            display_name=user.email.split("@")[0],
        )

    @staticmethod
    def identity_to_customer(user: UserIdentity) -> Customer:
        """
        Map an Identity context User to a Payment context Customer.

        Only transfers the data the Payment context needs.
        """
        return Customer(customer_id=user.user_id)

    @staticmethod
    def identity_to_driver(
        user: UserIdentity,
        vehicle: Vehicle,
    ) -> Driver:
        """
        Map an Identity context User to a Driver context Driver.

        Requires additional vehicle information that the Identity
        context doesn't have — the caller must provide it.
        """
        if not user.has_role(UserRole.DRIVER):
            raise ValueError(
                f"User {user.user_id} does not have the DRIVER role"
            )
        return Driver(
            driver_id=user.user_id,
            display_name=user.email.split("@")[0],
            vehicle=vehicle,
        )

    @staticmethod
    def rider_to_customer_id(rider: Rider) -> str:
        """
        Get the Payment context customer ID from a Ride context Rider.

        In practice, this is just the shared user_id that acts as
        the correlation ID across all contexts.
        """
        return rider.rider_id
