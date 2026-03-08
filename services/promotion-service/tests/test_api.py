"""Tests for promotion service — schema validation, config."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError


class TestCreatePromotionSchema:
    def test_valid_promotion(self):
        from schemas import CreatePromotionRequest
        req = CreatePromotionRequest(
            title="Summer Sale", promotion_type="seasonal",
            reward_type="percentage", reward_value=15.0,
        )
        assert req.title == "Summer Sale"

    def test_empty_title_fails(self):
        from schemas import CreatePromotionRequest
        with pytest.raises(ValidationError):
            CreatePromotionRequest(title="", promotion_type="seasonal", reward_type="fixed", reward_value=5.0)

    def test_zero_reward_fails(self):
        from schemas import CreatePromotionRequest
        with pytest.raises(ValidationError):
            CreatePromotionRequest(title="Bad", promotion_type="loyalty", reward_type="fixed", reward_value=0)

    def test_with_dates(self):
        from schemas import CreatePromotionRequest
        now = datetime.now(timezone.utc)
        req = CreatePromotionRequest(
            title="Holiday", promotion_type="seasonal",
            reward_type="free_ride", reward_value=1.0,
            start_date=now, end_date=now,
        )
        assert req.start_date is not None


class TestPromotionResponse:
    def test_valid_response(self):
        from schemas import PromotionResponse
        now = datetime.now(timezone.utc)
        resp = PromotionResponse(
            id="p-1", title="Welcome", promotion_type="referral",
            reward_type="fixed", reward_value=10.0, current_redemptions=5,
            is_active=True, created_at=now,
        )
        assert resp.current_redemptions == 5

    def test_list_response(self):
        from schemas import PromotionResponse, PromotionListResponse
        now = datetime.now(timezone.utc)
        promos = [PromotionResponse(
            id=f"p-{i}", title=f"Promo {i}", promotion_type="seasonal",
            reward_type="percentage", reward_value=10.0, current_redemptions=0,
            is_active=True, created_at=now,
        ) for i in range(3)]
        resp = PromotionListResponse(promotions=promos, count=3)
        assert resp.count == 3

    def test_redeem_response(self):
        from schemas import RedeemResponse
        resp = RedeemResponse(
            promotion_id="p-1", user_id="u-1", reward_type="fixed",
            reward_value=5.0, redeemed=True, message="OK",
        )
        assert resp.redeemed is True


class TestPromotionConfig:
    def test_defaults(self):
        from config import settings
        assert settings.service_name == "promotion-service"
        assert settings.service_port == 8073

    def test_database_url(self):
        from config import settings
        assert "postgresql+asyncpg" in settings.database_url
