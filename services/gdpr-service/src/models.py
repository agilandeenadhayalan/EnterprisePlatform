"""
Domain models for the GDPR service.

Manages data subject requests and consent records.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional


class RequestType(str, Enum):
    """GDPR data subject request types."""
    ACCESS = "access"
    ERASURE = "erasure"
    PORTABILITY = "portability"
    RECTIFICATION = "rectification"


class DSRStatus(str, Enum):
    """Data subject request statuses."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    REJECTED = "rejected"


class DataSubjectRequest:
    """A GDPR data subject request."""

    def __init__(
        self,
        id: str,
        request_type: str,
        subject_email: str,
        status: str = "pending",
        data_categories: Optional[list[str]] = None,
        submitted_at: Optional[datetime] = None,
        due_date: Optional[str] = None,
        completed_at: Optional[datetime] = None,
        notes: Optional[str] = None,
    ):
        self.id = id
        self.request_type = request_type
        self.subject_email = subject_email
        self.status = status
        self.data_categories = data_categories or []
        self.submitted_at = submitted_at or datetime.utcnow()
        self.due_date = due_date or (self.submitted_at + timedelta(days=30)).strftime("%Y-%m-%d")
        self.completed_at = completed_at
        self.notes = notes

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "request_type": self.request_type,
            "subject_email": self.subject_email,
            "status": self.status,
            "data_categories": self.data_categories,
            "submitted_at": self.submitted_at.isoformat(),
            "due_date": self.due_date,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "notes": self.notes,
        }


class ConsentRecord:
    """A GDPR consent record."""

    def __init__(
        self,
        id: str,
        subject_email: str,
        purpose: str,
        granted: bool = True,
        timestamp: Optional[datetime] = None,
    ):
        self.id = id
        self.subject_email = subject_email
        self.purpose = purpose
        self.granted = granted
        self.timestamp = timestamp or datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "subject_email": self.subject_email,
            "purpose": self.purpose,
            "granted": self.granted,
            "timestamp": self.timestamp.isoformat(),
        }
