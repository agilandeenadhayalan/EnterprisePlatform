"""
Tests for loyalty service — schema validation, config, and tier logic.
No database needed — these are pure unit tests.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest
from pydantic import ValidationError


class TestLoyaltySchemas:
    """Verify Pydantic schema validation for loyalty requests/responses."""

    def test_earn_points_request_valid(self):
        from schemas import EarnPointsRequest
        req = EarnPointsRequest(points=100, description="Ride completed")
        assert req.points == 100

    def test_earn_points_request_rejects_zero(self):
        from schemas import EarnPointsRequest
        with pytest.raises(ValidationError):
            EarnPointsRequest(points=0)

    def test_redeem_points_request_valid(self):
        from schemas import RedeemPointsRequest
        req = RedeemPointsRequest(points=50, description="Discount applied")
        assert req.points == 50

    def test_redeem_points_request_rejects_negative(self):
        from schemas import RedeemPointsRequest
        with pytest.raises(ValidationError):
            RedeemPointsRequest(points=-10)

    def test_loyalty_balance_response(self):
        from schemas import LoyaltyBalanceResponse
        resp = LoyaltyBalanceResponse(
            user_id="user-1",
            total_points=500,
            tier="bronze",
            lifetime_points=500,
        )
        assert resp.tier == "bronze"

    def test_loyalty_transaction_response(self):
        from schemas import LoyaltyTransactionResponse
        now = datetime.now(timezone.utc)
        resp = LoyaltyTransactionResponse(
            id="txn-1",
            user_id="user-1",
            points=100,
            transaction_type="earn",
            created_at=now,
        )
        assert resp.description is None

    def test_loyalty_transaction_list(self):
        from schemas import LoyaltyTransactionResponse, LoyaltyTransactionListResponse
        now = datetime.now(timezone.utc)
        txns = [
            LoyaltyTransactionResponse(
                id=f"txn-{i}", user_id="user-1", points=100,
                transaction_type="earn", created_at=now,
            )
            for i in range(3)
        ]
        resp = LoyaltyTransactionListResponse(transactions=txns, count=3)
        assert resp.count == 3

    def test_loyalty_tier_response(self):
        from schemas import LoyaltyTierResponse
        resp = LoyaltyTierResponse(
            user_id="user-1",
            tier="silver",
            lifetime_points=2000,
            next_tier="gold",
            points_to_next_tier=3000,
        )
        assert resp.next_tier == "gold"

    def test_earn_redeem_response(self):
        from schemas import EarnRedeemResponse
        resp = EarnRedeemResponse(
            user_id="user-1",
            points_changed=100,
            new_balance=600,
            tier="bronze",
            message="Earned 100 points",
        )
        assert resp.new_balance == 600


class TestTierLogic:
    """Verify tier calculation logic."""

    def test_bronze_tier(self):
        from repository import calculate_tier
        assert calculate_tier(0) == "bronze"
        assert calculate_tier(999) == "bronze"

    def test_silver_tier(self):
        from repository import calculate_tier
        assert calculate_tier(1000) == "silver"
        assert calculate_tier(4999) == "silver"

    def test_gold_tier(self):
        from repository import calculate_tier
        assert calculate_tier(5000) == "gold"

    def test_diamond_tier(self):
        from repository import calculate_tier
        assert calculate_tier(50000) == "diamond"

    def test_next_tier_info(self):
        from repository import get_next_tier_info
        next_tier, points_needed = get_next_tier_info(800)
        assert next_tier == "silver"
        assert points_needed == 200

    def test_next_tier_at_max(self):
        from repository import get_next_tier_info
        next_tier, points_needed = get_next_tier_info(100000)
        assert next_tier is None
        assert points_needed is None


class TestLoyaltyConfig:
    """Verify loyalty service configuration defaults."""

    def test_config_defaults(self):
        from config import settings
        assert settings.service_name == "loyalty-service"
        assert settings.service_port == 8099

    def test_database_url_format(self):
        from config import settings
        assert settings.database_url.startswith("postgresql+asyncpg://")

    def test_kafka_config(self):
        from config import settings
        assert settings.kafka_bootstrap_servers == "kafka:9092"
