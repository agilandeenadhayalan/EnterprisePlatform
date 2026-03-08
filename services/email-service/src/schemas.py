"""
Pydantic request/response schemas for the email service API.
"""

from typing import Optional, List, Dict

from pydantic import BaseModel, Field


# ── Request schemas ──

class EmailSendRequest(BaseModel):
    """POST /email/send — send a single email."""
    to: str = Field(..., description="Recipient email address")
    subject: str = Field(..., max_length=255)
    body: str = Field(..., description="Email body (plain text or HTML)")
    is_html: bool = Field(False, description="Whether body is HTML")


class EmailSendTemplateRequest(BaseModel):
    """POST /email/send-template — send an email using a template."""
    to: str = Field(..., description="Recipient email address")
    template_id: str = Field(..., description="Template identifier")
    variables: Dict[str, str] = Field(default_factory=dict, description="Template variables")


# ── Response schemas ──

class EmailSendResponse(BaseModel):
    """Response after sending an email."""
    message_id: str
    status: str = "queued"
    to: str


class EmailTemplateResponse(BaseModel):
    """Single email template."""
    id: str
    name: str
    subject: str
    description: Optional[str] = None


class EmailTemplateListResponse(BaseModel):
    """GET /email/templates — list available email templates."""
    templates: List[EmailTemplateResponse]
    count: int
