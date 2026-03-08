"""
Test fixtures for driver service.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


@pytest.fixture
def sample_driver_data():
    """Sample driver registration data."""
    return {
        "user_id": "550e8400-e29b-41d4-a716-446655440000",
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.driver@test.com",
        "phone": "+1234567890",
        "license_number": "DL-12345",
        "vehicle_type": "sedan",
        "vehicle_make": "Toyota",
        "vehicle_model": "Camry",
        "vehicle_year": 2022,
        "vehicle_plate": "ABC-1234",
    }


@pytest.fixture
def mock_driver():
    """Mock driver ORM object."""
    driver = MagicMock()
    driver.id = "660e8400-e29b-41d4-a716-446655440001"
    driver.user_id = "550e8400-e29b-41d4-a716-446655440000"
    driver.first_name = "John"
    driver.last_name = "Doe"
    driver.email = "john.driver@test.com"
    driver.phone = "+1234567890"
    driver.license_number = "DL-12345"
    driver.vehicle_type = "sedan"
    driver.vehicle_make = "Toyota"
    driver.vehicle_model = "Camry"
    driver.vehicle_year = 2022
    driver.vehicle_plate = "ABC-1234"
    driver.rating = 4.8
    driver.total_trips = 150
    driver.acceptance_rate = 0.92
    driver.is_active = True
    driver.is_verified = True
    driver.status = "online"
    driver.latitude = 40.7128
    driver.longitude = -74.0060
    driver.created_at = datetime(2024, 1, 1)
    driver.updated_at = datetime(2024, 1, 1)
    return driver


@pytest.fixture
def mock_producer():
    """Mock Kafka producer."""
    producer = AsyncMock()
    producer.send_event = AsyncMock(return_value=True)
    return producer
