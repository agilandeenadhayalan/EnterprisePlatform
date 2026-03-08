"""Tests for wallet service."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

class TestTopupSchema:
    def test_valid_topup(self):
        from schemas import TopupRequest
        req = TopupRequest(amount=50.0, description="Added funds")
        assert req.amount == 50.0

    def test_zero_amount_fails(self):
        from schemas import TopupRequest
        with pytest.raises(ValidationError):
            TopupRequest(amount=0)

    def test_negative_amount_fails(self):
        from schemas import TopupRequest
        with pytest.raises(ValidationError):
            TopupRequest(amount=-10.0)

class TestDebitSchema:
    def test_valid_debit(self):
        from schemas import DebitRequest
        req = DebitRequest(amount=25.0)
        assert req.amount == 25.0

    def test_zero_fails(self):
        from schemas import DebitRequest
        with pytest.raises(ValidationError):
            DebitRequest(amount=0)

class TestWalletResponse:
    def test_wallet_response(self):
        from schemas import WalletResponse
        now = datetime.now(timezone.utc)
        resp = WalletResponse(id="w-1", user_id="u-1", balance=100.0, currency="USD", created_at=now, updated_at=now)
        assert resp.balance == 100.0

    def test_transaction_response(self):
        from schemas import WalletTransactionResponse
        now = datetime.now(timezone.utc)
        resp = WalletTransactionResponse(id="t-1", wallet_id="w-1", user_id="u-1",
            transaction_type="topup", amount=50.0, balance_after=150.0, created_at=now)
        assert resp.transaction_type == "topup"

    def test_transaction_list(self):
        from schemas import WalletTransactionResponse, TransactionListResponse
        now = datetime.now(timezone.utc)
        txns = [WalletTransactionResponse(id=f"t-{i}", wallet_id="w-1", user_id="u-1",
            transaction_type="topup", amount=10.0, balance_after=10.0*(i+1), created_at=now) for i in range(3)]
        resp = TransactionListResponse(transactions=txns, count=3)
        assert resp.count == 3

    def test_debit_transaction(self):
        from schemas import WalletTransactionResponse
        now = datetime.now(timezone.utc)
        resp = WalletTransactionResponse(id="t-2", wallet_id="w-1", user_id="u-1",
            transaction_type="debit", amount=25.0, balance_after=75.0, description="Trip payment", created_at=now)
        assert resp.transaction_type == "debit"

class TestWalletConfig:
    def test_defaults(self):
        from config import settings
        assert settings.service_name == "wallet-service"
        assert settings.service_port == 8084

    def test_database_url(self):
        from config import settings
        assert "postgresql+asyncpg" in settings.database_url
