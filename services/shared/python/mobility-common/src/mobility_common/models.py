"""
Domain models shared across all services.

These Pydantic models define the core domain entities (User, Driver, Trip, etc.)
that are referenced by multiple microservices. By centralizing them here, we
ensure schema consistency across 155 services.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Enums ──


class UserRole(str, Enum):
    RIDER = "rider"
    DRIVER = "driver"
    ADMIN = "admin"
    SUPPORT = "support"


class TripStatus(str, Enum):
    REQUESTED = "requested"
    DRIVER_ASSIGNED = "driver_assigned"
    DRIVER_EN_ROUTE = "driver_en_route"
    ARRIVED = "arrived"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PaymentMethod(str, Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    WALLET = "wallet"
    CASH = "cash"


# ── Core Models ──


class Location(BaseModel):
    """GPS coordinate with optional zone metadata."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    zone_id: Optional[int] = None
    zone_name: Optional[str] = None


class User(BaseModel):
    """Base user entity shared across identity and user services."""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    email: str
    full_name: str
    role: UserRole = UserRole.RIDER
    phone: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime = Field(default_factory=datetime.now)


class Driver(BaseModel):
    """Driver profile extending User with driving-specific fields."""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID
    license_number: str
    vehicle_id: Optional[uuid.UUID] = None
    current_location: Optional[Location] = None
    is_available: bool = False
    rating: float = Field(default=5.0, ge=1.0, le=5.0)
    total_trips: int = 0


class TripRequest(BaseModel):
    """A ride request from a rider."""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    rider_id: uuid.UUID
    pickup: Location
    dropoff: Location
    requested_at: datetime = Field(default_factory=datetime.now)
    estimated_fare: Optional[float] = None
    payment_method: PaymentMethod = PaymentMethod.CREDIT_CARD


class Trip(BaseModel):
    """A trip from request through completion."""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    rider_id: uuid.UUID
    driver_id: Optional[uuid.UUID] = None
    pickup: Location
    dropoff: Location
    status: TripStatus = TripStatus.REQUESTED
    fare_amount: Optional[float] = None
    distance_miles: Optional[float] = None
    duration_minutes: Optional[float] = None
    requested_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
