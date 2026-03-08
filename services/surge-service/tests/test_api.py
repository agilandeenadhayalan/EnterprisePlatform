"""
Tests for surge service — calculator edge cases, schema validation, config.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError


class TestSurgeCalculator:
    """Test surge calculation edge cases."""

    def test_equal_supply_demand(self):
        """Equal supply and demand should produce no surge."""
        from calculator import calculate_surge
        assert calculate_surge(10, 10) == 1.0

    def test_low_demand(self):
        """Demand lower than supply should produce no surge."""
        from calculator import calculate_surge
        assert calculate_surge(5, 10) == 1.0

    def test_zero_demand(self):
        """Zero demand should produce no surge."""
        from calculator import calculate_surge
        assert calculate_surge(0, 10) == 1.0

    def test_zero_supply(self):
        """Zero supply should produce max surge."""
        from calculator import calculate_surge
        assert calculate_surge(10, 0) == 5.0

    def test_double_demand(self):
        """2x demand should produce moderate surge."""
        from calculator import calculate_surge
        result = calculate_surge(20, 10)
        assert 1.5 <= result <= 2.5

    def test_high_demand(self):
        """Very high demand should approach cap."""
        from calculator import calculate_surge
        result = calculate_surge(100, 5)
        assert result <= 5.0

    def test_surge_capped_at_five(self):
        """Surge should never exceed 5.0."""
        from calculator import calculate_surge
        result = calculate_surge(1000, 1)
        assert result == 5.0

    def test_negative_demand(self):
        """Negative demand treated as zero — no surge."""
        from calculator import calculate_surge
        assert calculate_surge(-5, 10) == 1.0

    def test_returns_float(self):
        """Result should always be a float."""
        from calculator import calculate_surge
        assert isinstance(calculate_surge(15, 10), float)

    def test_moderate_ratio(self):
        """Moderate demand ratio should produce reasonable surge."""
        from calculator import calculate_surge
        result = calculate_surge(30, 10)
        assert 1.0 < result < 5.0


class TestSurgeSchemas:
    """Verify Pydantic schema validation for surge requests/responses."""

    def test_surge_update_valid(self):
        from schemas import SurgeUpdateRequest
        req = SurgeUpdateRequest(surge_multiplier=1.5, demand_count=20, supply_count=10)
        assert req.surge_multiplier == 1.5

    def test_surge_update_max(self):
        from schemas import SurgeUpdateRequest
        with pytest.raises(ValidationError):
            SurgeUpdateRequest(surge_multiplier=15.0)


class TestSurgeConfig:
    """Verify surge service configuration defaults."""

    def test_config_defaults(self):
        from config import settings
        assert settings.service_name == "surge-service"
        assert settings.service_port == 8071

    def test_kafka_config(self):
        from config import settings
        assert settings.kafka_bootstrap_servers == "kafka:9092"
