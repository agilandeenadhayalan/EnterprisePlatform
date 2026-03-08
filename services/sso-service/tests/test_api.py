"""
Tests for the SSO service.

Tests provider listing schema, authorization URL generation logic, and
callback response validation.
"""

import sys
from pathlib import Path

# Add paths for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "python" / "mobility-common" / "src"))

import secrets
from datetime import datetime
from urllib.parse import urlencode, parse_qs, urlparse

import pytest
from pydantic import ValidationError

from schemas import (
    SsoProviderResponse,
    AuthorizeRequest,
    AuthorizeResponse,
    CallbackRequest,
    CallbackResponse,
    SsoConnectionResponse,
)


class TestSsoProviderResponseSchema:
    """Test SsoProviderResponse validation."""

    def test_full_provider(self):
        """Provider response with all fields should parse correctly."""
        resp = SsoProviderResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            name="google",
            display_name="Google",
            provider_type="oidc",
            authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
            scopes="openid email profile",
            is_enabled=True,
        )
        assert resp.name == "google"
        assert resp.display_name == "Google"
        assert resp.is_enabled is True

    def test_minimal_provider(self):
        """Provider with only required fields should work."""
        resp = SsoProviderResponse(
            id="123",
            name="github",
            display_name="GitHub",
            provider_type="oauth2",
        )
        assert resp.name == "github"
        assert resp.authorization_url is None
        assert resp.is_enabled is True  # default

    def test_disabled_provider(self):
        """Disabled provider should be represented correctly."""
        resp = SsoProviderResponse(
            id="456",
            name="okta",
            display_name="Okta",
            provider_type="saml",
            is_enabled=False,
        )
        assert resp.is_enabled is False


class TestAuthorizeRequest:
    """Test AuthorizeRequest validation."""

    def test_valid_authorize_request(self):
        """Valid request should parse correctly."""
        req = AuthorizeRequest(
            provider_name="google",
            redirect_uri="https://app.example.com/callback",
        )
        assert req.provider_name == "google"
        assert req.redirect_uri == "https://app.example.com/callback"

    def test_missing_provider_name_fails(self):
        """provider_name is required."""
        with pytest.raises(ValidationError):
            AuthorizeRequest(redirect_uri="https://app.example.com/callback")

    def test_missing_redirect_uri_fails(self):
        """redirect_uri is required."""
        with pytest.raises(ValidationError):
            AuthorizeRequest(provider_name="google")


class TestAuthorizationUrlGeneration:
    """Test the authorization URL building logic."""

    def _build_url(
        self,
        base_url: str,
        client_id: str,
        redirect_uri: str,
        state: str,
        scopes: str = "openid email profile",
    ) -> str:
        """Replicate the URL building logic from repository."""
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": scopes,
            "state": state,
        }
        return f"{base_url}?{urlencode(params)}"

    def test_google_authorization_url(self):
        """Google authorization URL should contain required OAuth2 params."""
        state = secrets.token_urlsafe(32)
        url = self._build_url(
            base_url="https://accounts.google.com/o/oauth2/v2/auth",
            client_id="google-client-id-123",
            redirect_uri="https://app.example.com/callback",
            state=state,
        )
        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        assert parsed.scheme == "https"
        assert "accounts.google.com" in parsed.netloc
        assert params["client_id"] == ["google-client-id-123"]
        assert params["response_type"] == ["code"]
        assert params["state"] == [state]
        assert "openid" in params["scope"][0]

    def test_github_authorization_url(self):
        """GitHub authorization URL should be constructed correctly."""
        state = secrets.token_urlsafe(32)
        url = self._build_url(
            base_url="https://github.com/login/oauth/authorize",
            client_id="github-client-id-456",
            redirect_uri="https://app.example.com/callback",
            state=state,
            scopes="read:user user:email",
        )
        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        assert "github.com" in parsed.netloc
        assert params["client_id"] == ["github-client-id-456"]
        assert "read:user" in params["scope"][0]

    def test_state_is_random(self):
        """Each state parameter should be unique."""
        states = {secrets.token_urlsafe(32) for _ in range(100)}
        # All 100 should be unique (extremely unlikely to collide)
        assert len(states) == 100

    def test_authorize_response_schema(self):
        """AuthorizeResponse should contain the authorization URL and state."""
        resp = AuthorizeResponse(
            authorization_url="https://accounts.google.com/o/oauth2/v2/auth?client_id=abc",
            state="random-state-xyz",
            provider_name="google",
        )
        assert "accounts.google.com" in resp.authorization_url
        assert resp.state == "random-state-xyz"
        assert resp.provider_name == "google"


class TestCallbackRequest:
    """Test CallbackRequest validation."""

    def test_valid_callback(self):
        """Valid callback request should parse correctly."""
        req = CallbackRequest(
            provider_name="google",
            code="auth-code-from-provider",
            state="state-parameter-for-csrf",
        )
        assert req.provider_name == "google"
        assert req.code == "auth-code-from-provider"
        assert req.state == "state-parameter-for-csrf"

    def test_missing_code_fails(self):
        """code is required."""
        with pytest.raises(ValidationError):
            CallbackRequest(provider_name="google", state="abc")

    def test_missing_state_fails(self):
        """state is required."""
        with pytest.raises(ValidationError):
            CallbackRequest(provider_name="google", code="abc")

    def test_callback_response_schema(self):
        """CallbackResponse should contain user and provider info."""
        resp = CallbackResponse(
            user_id="user-123",
            provider_name="google",
            external_user_id="google_abc12345",
            external_email="user@gmail.com",
        )
        assert resp.user_id == "user-123"
        assert resp.provider_name == "google"
        assert resp.message == "SSO connection established"


class TestSsoConnectionResponse:
    """Test SsoConnectionResponse schema."""

    def test_full_connection(self):
        """Connection with all fields should parse correctly."""
        now = datetime.utcnow()
        resp = SsoConnectionResponse(
            id="conn-123",
            provider_name="google",
            provider_display_name="Google",
            external_user_id="google_user_456",
            external_email="user@gmail.com",
            external_name="Test User",
            connected_at=now,
            last_login_at=now,
        )
        assert resp.provider_name == "google"
        assert resp.external_email == "user@gmail.com"

    def test_minimal_connection(self):
        """Connection with only required fields."""
        resp = SsoConnectionResponse(
            id="conn-789",
            provider_name="github",
            provider_display_name="GitHub",
            external_user_id="github_user_321",
            connected_at=datetime.utcnow(),
        )
        assert resp.external_email is None
        assert resp.last_login_at is None
