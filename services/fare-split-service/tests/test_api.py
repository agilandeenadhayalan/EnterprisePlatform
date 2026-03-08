"""Tests for fare split service."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

class TestCreateSplitSchema:
    def test_valid_split(self):
        from schemas import CreateSplitRequest, ParticipantInput
        req = CreateSplitRequest(
            trip_id="t-1", initiator_id="u-1", total_amount=30.0,
            participants=[ParticipantInput(user_id="u-1", share_amount=15.0), ParticipantInput(user_id="u-2", share_amount=15.0)],
        )
        assert len(req.participants) == 2

    def test_one_participant_fails(self):
        from schemas import CreateSplitRequest, ParticipantInput
        with pytest.raises(ValidationError):
            CreateSplitRequest(
                trip_id="t-1", initiator_id="u-1", total_amount=30.0,
                participants=[ParticipantInput(user_id="u-1", share_amount=30.0)],
            )

    def test_zero_total_fails(self):
        from schemas import CreateSplitRequest, ParticipantInput
        with pytest.raises(ValidationError):
            CreateSplitRequest(
                trip_id="t-1", initiator_id="u-1", total_amount=0,
                participants=[ParticipantInput(user_id="u-1", share_amount=0), ParticipantInput(user_id="u-2", share_amount=0)],
            )

    def test_zero_share_fails(self):
        from schemas import ParticipantInput
        with pytest.raises(ValidationError):
            ParticipantInput(user_id="u-1", share_amount=0)

class TestSplitResponse:
    def test_split_response(self):
        from schemas import SplitResponse
        now = datetime.now(timezone.utc)
        resp = SplitResponse(id="s-1", trip_id="t-1", initiator_id="u-1", total_amount=30.0, status="pending", created_at=now)
        assert resp.status == "pending"

    def test_participant_response(self):
        from schemas import ParticipantResponse
        now = datetime.now(timezone.utc)
        resp = ParticipantResponse(id="p-1", split_id="s-1", user_id="u-1", share_amount=15.0, status="pending", created_at=now)
        assert resp.share_amount == 15.0

    def test_accept_response(self):
        from schemas import AcceptSplitResponse
        resp = AcceptSplitResponse(split_id="s-1", user_id="u-1", status="accepted", message="OK")
        assert resp.status == "accepted"

class TestFareSplitConfig:
    def test_defaults(self):
        from config import settings
        assert settings.service_name == "fare-split-service"
        assert settings.service_port == 8085

    def test_database_url(self):
        from config import settings
        assert "postgresql+asyncpg" in settings.database_url
