"""Tests for discount service — schema validation, config."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError


class TestValidateDiscountSchema:
    def test_valid_request(self):
        from schemas import ValidateDiscountRequest
        req = ValidateDiscountRequest(code="SAVE20", fare_amount=25.0)
        assert req.code == "SAVE20"

    def test_empty_code_fails(self):
        from schemas import ValidateDiscountRequest
        with pytest.raises(ValidationError):
            ValidateDiscountRequest(code="", fare_amount=10.0)

    def test_optional_fare_amount(self):
        from schemas import ValidateDiscountRequest
        req = ValidateDiscountRequest(code="TEST")
        assert req.fare_amount is None


class TestApplyDiscountSchema:
    def test_valid_apply(self):
        from schemas import ApplyDiscountRequest
        req = ApplyDiscountRequest(code="SAVE20", fare_amount=30.0)
        assert req.fare_amount == 30.0

    def test_zero_fare_fails(self):
        from schemas import ApplyDiscountRequest
        with pytest.raises(ValidationError):
            ApplyDiscountRequest(code="X", fare_amount=0.0)


class TestCreateDiscountSchema:
    def test_valid_percentage(self):
        from schemas import CreateDiscountRequest
        req = CreateDiscountRequest(code="NEW20", discount_type="percentage", discount_value=20.0)
        assert req.discount_type == "percentage"

    def test_valid_fixed(self):
        from schemas import CreateDiscountRequest
        req = CreateDiscountRequest(code="FLAT5", discount_type="fixed", discount_value=5.0)
        assert req.discount_type == "fixed"

    def test_invalid_type_fails(self):
        from schemas import CreateDiscountRequest
        with pytest.raises(ValidationError):
            CreateDiscountRequest(code="BAD", discount_type="bogus", discount_value=10.0)


class TestDiscountResponses:
    def test_validate_response(self):
        from schemas import ValidateDiscountResponse
        resp = ValidateDiscountResponse(code="SAVE20", is_valid=True, discount_type="percentage", discount_value=20.0)
        assert resp.is_valid is True

    def test_apply_response(self):
        from schemas import ApplyDiscountResponse
        resp = ApplyDiscountResponse(code="SAVE20", original_fare=25.0, discount_amount=5.0, final_fare=20.0)
        assert resp.final_fare == 20.0


class TestDiscountConfig:
    def test_defaults(self):
        from config import settings
        assert settings.service_name == "discount-service"
        assert settings.service_port == 8072
