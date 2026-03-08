"""
Tests for support ticket service — schema validation, config, and imports.
No database needed — these are pure unit tests.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest
from pydantic import ValidationError


class TestTicketSchemas:
    """Verify Pydantic schema validation for support ticket requests/responses."""

    def test_create_ticket_request_valid(self):
        from schemas import CreateTicketRequest
        req = CreateTicketRequest(
            user_id="user-1",
            subject="Cannot complete ride",
            description="The app crashes when I try to complete my ride.",
        )
        assert req.category == "general"
        assert req.priority == "medium"

    def test_create_ticket_request_custom_fields(self):
        from schemas import CreateTicketRequest
        req = CreateTicketRequest(
            user_id="user-1",
            subject="Billing issue",
            description="I was overcharged for my last ride.",
            category="billing",
            priority="high",
        )
        assert req.category == "billing"
        assert req.priority == "high"

    def test_update_ticket_status_request(self):
        from schemas import UpdateTicketStatusRequest
        req = UpdateTicketStatusRequest(status="in_progress", assigned_to="agent-1")
        assert req.status == "in_progress"

    def test_update_ticket_status_no_assignment(self):
        from schemas import UpdateTicketStatusRequest
        req = UpdateTicketStatusRequest(status="resolved")
        assert req.assigned_to is None

    def test_ticket_response_valid(self):
        from schemas import TicketResponse
        now = datetime.now(timezone.utc)
        resp = TicketResponse(
            id="ticket-1",
            user_id="user-1",
            subject="Test",
            description="Test description",
            category="general",
            priority="medium",
            status="open",
            created_at=now,
            updated_at=now,
        )
        assert resp.assigned_to is None
        assert resp.resolved_at is None

    def test_ticket_response_resolved(self):
        from schemas import TicketResponse
        now = datetime.now(timezone.utc)
        resp = TicketResponse(
            id="ticket-1",
            user_id="user-1",
            subject="Test",
            description="Test description",
            category="general",
            priority="medium",
            status="resolved",
            assigned_to="agent-1",
            resolved_at=now,
            created_at=now,
            updated_at=now,
        )
        assert resp.status == "resolved"
        assert resp.assigned_to == "agent-1"

    def test_ticket_list_response(self):
        from schemas import TicketResponse, TicketListResponse
        now = datetime.now(timezone.utc)
        tickets = [
            TicketResponse(
                id=f"ticket-{i}",
                user_id="user-1",
                subject=f"Issue {i}",
                description=f"Description {i}",
                category="general",
                priority="medium",
                status="open",
                created_at=now,
                updated_at=now,
            )
            for i in range(3)
        ]
        resp = TicketListResponse(tickets=tickets, count=3)
        assert resp.count == 3

    def test_ticket_list_empty(self):
        from schemas import TicketListResponse
        resp = TicketListResponse(tickets=[], count=0)
        assert resp.count == 0


class TestTicketConfig:
    """Verify support ticket service configuration defaults."""

    def test_config_defaults(self):
        from config import settings
        assert settings.service_name == "support-ticket-service"
        assert settings.service_port == 8102

    def test_database_url_format(self):
        from config import settings
        assert settings.database_url.startswith("postgresql+asyncpg://")

    def test_kafka_config(self):
        from config import settings
        assert settings.kafka_bootstrap_servers == "kafka:9092"


class TestImports:
    """Verify that shared library imports work."""

    def test_error_helpers_import(self):
        from mobility_common.fastapi.errors import not_found
        assert callable(not_found)

    def test_create_app_import(self):
        from mobility_common.fastapi.app import create_app
        assert callable(create_app)
