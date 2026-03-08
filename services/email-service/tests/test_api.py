"""
Tests for email service — schema validation, config, and repository logic.
No database needed — these are pure unit tests.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import pytest


class TestEmailSchemas:
    """Verify Pydantic schema validation for email requests/responses."""

    def test_email_send_request_valid(self):
        from schemas import EmailSendRequest
        req = EmailSendRequest(
            to="user@example.com",
            subject="Test Subject",
            body="Hello, this is a test email.",
        )
        assert req.to == "user@example.com"
        assert req.is_html is False

    def test_email_send_request_html(self):
        from schemas import EmailSendRequest
        req = EmailSendRequest(
            to="user@example.com",
            subject="Test",
            body="<h1>Hello</h1>",
            is_html=True,
        )
        assert req.is_html is True

    def test_email_template_request_valid(self):
        from schemas import EmailSendTemplateRequest
        req = EmailSendTemplateRequest(
            to="user@example.com",
            template_id="welcome",
            variables={"name": "John"},
        )
        assert req.template_id == "welcome"
        assert req.variables["name"] == "John"

    def test_email_template_request_no_variables(self):
        from schemas import EmailSendTemplateRequest
        req = EmailSendTemplateRequest(
            to="user@example.com",
            template_id="welcome",
        )
        assert req.variables == {}

    def test_email_send_response(self):
        from schemas import EmailSendResponse
        resp = EmailSendResponse(
            message_id="msg-123",
            to="user@example.com",
        )
        assert resp.status == "queued"

    def test_email_template_response(self):
        from schemas import EmailTemplateResponse
        resp = EmailTemplateResponse(
            id="welcome",
            name="Welcome Email",
            subject="Welcome to Smart Mobility!",
        )
        assert resp.description is None

    def test_email_template_list_response(self):
        from schemas import EmailTemplateResponse, EmailTemplateListResponse
        templates = [
            EmailTemplateResponse(id="welcome", name="Welcome", subject="Welcome!"),
            EmailTemplateResponse(id="receipt", name="Receipt", subject="Your Receipt"),
        ]
        resp = EmailTemplateListResponse(templates=templates, count=2)
        assert resp.count == 2


class TestEmailRepository:
    """Verify stubbed email repository logic."""

    @pytest.mark.asyncio
    async def test_send_email_returns_message_id(self):
        from repository import EmailRepository
        repo = EmailRepository()
        msg_id = await repo.send_email("user@test.com", "Subject", "Body")
        assert msg_id is not None

    @pytest.mark.asyncio
    async def test_get_templates_returns_list(self):
        from repository import EmailRepository
        repo = EmailRepository()
        templates = await repo.get_templates()
        assert len(templates) >= 3
        assert templates[0]["id"] == "welcome"


class TestEmailConfig:
    """Verify email service configuration defaults."""

    def test_config_defaults(self):
        from config import settings
        assert settings.service_name == "email-service"
        assert settings.service_port == 8092

    def test_kafka_config(self):
        from config import settings
        assert settings.kafka_bootstrap_servers == "kafka:9092"
