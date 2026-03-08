"""
Pydantic request/response schemas for the SSO service API.

Defines shapes for SSO provider listing, authorization flow, and
connection management.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# -- Request schemas --

class AuthorizeRequest(BaseModel):
    """POST /sso/authorize — initiate SSO flow."""
    provider_name: str = Field(..., description="SSO provider name, e.g. 'google', 'github'")
    redirect_uri: str = Field(..., description="URL to redirect back to after SSO authorization")


class CallbackRequest(BaseModel):
    """POST /sso/callback — handle SSO callback after user authorizes."""
    provider_name: str = Field(..., description="SSO provider name")
    code: str = Field(..., description="Authorization code from the SSO provider")
    state: str = Field(..., description="State parameter for CSRF protection")


# -- Response schemas --

class SsoProviderResponse(BaseModel):
    """SSO provider data returned from list endpoint."""
    id: str
    name: str
    display_name: str
    provider_type: str
    authorization_url: Optional[str] = None
    scopes: Optional[str] = None
    is_enabled: bool = True


class AuthorizeResponse(BaseModel):
    """Response from the authorize endpoint — the URL to redirect the user to."""
    authorization_url: str
    state: str
    provider_name: str


class CallbackResponse(BaseModel):
    """Response from the callback endpoint — confirms the SSO link."""
    user_id: str
    provider_name: str
    external_user_id: str
    external_email: Optional[str] = None
    message: str = "SSO connection established"


class SsoConnectionResponse(BaseModel):
    """An SSO connection for a user."""
    id: str
    provider_name: str
    provider_display_name: str
    external_user_id: str
    external_email: Optional[str] = None
    external_name: Optional[str] = None
    connected_at: datetime
    last_login_at: Optional[datetime] = None


class MessageResponse(BaseModel):
    """Simple acknowledgement response."""
    message: str
