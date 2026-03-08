"""
Tests for subscription service — schema validation, config, and plans logic.
No database needed — these are pure unit tests.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest


class TestSubscriptionSchemas:
    """Verify Pydantic schema validation for subscription requests/responses."""

    def test_create_subscription_request(self):
        from schemas import CreateSubscriptionRequest
        req = CreateSubscriptionRequest(user_id="user-1", plan_id="premium")
        assert req.plan_id == "premium"

    def test_subscription_response(self):
        from schemas import SubscriptionResponse
        now = datetime.now(timezone.utc)
        resp = SubscriptionResponse(
            id="sub-1",
            user_id="user-1",
            plan_id="premium",
            status="active",
            price_per_month=19.99,
            started_at=now,
            created_at=now,
        )
        assert resp.status == "active"
        assert resp.cancelled_at is None

    def test_subscription_response_cancelled(self):
        from schemas import SubscriptionResponse
        now = datetime.now(timezone.utc)
        resp = SubscriptionResponse(
            id="sub-1",
            user_id="user-1",
            plan_id="basic",
            status="cancelled",
            price_per_month=9.99,
            started_at=now,
            cancelled_at=now,
            created_at=now,
        )
        assert resp.status == "cancelled"
        assert resp.cancelled_at is not None

    def test_plan_response(self):
        from schemas import PlanResponse
        resp = PlanResponse(
            id="basic",
            name="Basic",
            price_per_month=9.99,
            description="Essential features",
            features=["Priority booking", "Email support"],
        )
        assert len(resp.features) == 2

    def test_plan_list_response(self):
        from schemas import PlanResponse, PlanListResponse
        plans = [
            PlanResponse(id="basic", name="Basic", price_per_month=9.99,
                        description="Basic plan", features=["Feature 1"]),
            PlanResponse(id="premium", name="Premium", price_per_month=19.99,
                        description="Premium plan", features=["Feature 1", "Feature 2"]),
        ]
        resp = PlanListResponse(plans=plans, count=2)
        assert resp.count == 2

    def test_cancel_response(self):
        from schemas import CancelResponse
        now = datetime.now(timezone.utc)
        resp = CancelResponse(id="sub-1", status="cancelled", cancelled_at=now)
        assert resp.message == "Subscription cancelled"


class TestSubscriptionPlans:
    """Verify subscription plans data."""

    def test_plans_exist(self):
        from repository import PLANS
        assert len(PLANS) == 3

    def test_plans_have_required_fields(self):
        from repository import PLANS
        for plan in PLANS:
            assert "id" in plan
            assert "name" in plan
            assert "price_per_month" in plan
            assert "features" in plan

    def test_plan_prices_ascending(self):
        from repository import PLANS
        prices = [p["price_per_month"] for p in PLANS]
        assert prices == sorted(prices)


class TestSubscriptionConfig:
    """Verify subscription service configuration defaults."""

    def test_config_defaults(self):
        from config import settings
        assert settings.service_name == "subscription-service"
        assert settings.service_port == 8101

    def test_database_url_format(self):
        from config import settings
        assert settings.database_url.startswith("postgresql+asyncpg://")

    def test_kafka_config(self):
        from config import settings
        assert settings.kafka_bootstrap_servers == "kafka:9092"
