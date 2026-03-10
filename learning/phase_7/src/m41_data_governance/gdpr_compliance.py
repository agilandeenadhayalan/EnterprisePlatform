"""
GDPR compliance — consent management, subject rights, data retention.

WHY THIS MATTERS:
GDPR grants individuals strong rights over their personal data. A
mobility platform operating in (or serving riders from) the EU must:
  - Obtain explicit consent before processing data for non-essential purposes
  - Respond to data subject requests (access, erasure) within 30 days
  - Enforce data retention policies — delete data when the legal basis expires

Non-compliance penalties can reach 4% of global annual revenue or
20 million EUR, whichever is greater. Automating compliance processes
is essential at scale.

Key concepts:
  - Consent management: tracking per-purpose consent with expiry
  - Data subject rights: handling access, erasure, portability requests
  - Retention policies: automatic purging of expired data
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid


class ConsentPurpose(Enum):
    """Purposes for which data processing consent may be granted.

    GDPR requires separate consent for each processing purpose.
    Essential processing doesn't require consent but is included
    for completeness.
    """

    MARKETING = "marketing"
    ANALYTICS = "analytics"
    PERSONALIZATION = "personalization"
    ESSENTIAL = "essential"
    THIRD_PARTY = "third_party"


@dataclass
class ConsentRecord:
    """Record of a data subject's consent decision.

    Tracks who gave consent, for what purpose, when, and when it expires.
    """

    subject_email: str
    purpose: ConsentPurpose
    granted: bool
    timestamp: datetime
    expiry_date: datetime = None


class ConsentManager:
    """Manage per-subject, per-purpose consent records.

    Maintains a history of consent grants and withdrawals. The latest
    record for each (subject, purpose) pair determines current status.
    """

    def __init__(self):
        self._records: list = []

    def grant(self, subject: str, purpose: ConsentPurpose) -> ConsentRecord:
        """Record consent being granted.

        Creates a new ConsentRecord with granted=True and current timestamp.
        Default expiry is 365 days from now.
        """
        now = datetime.utcnow()
        record = ConsentRecord(
            subject_email=subject,
            purpose=purpose,
            granted=True,
            timestamp=now,
            expiry_date=now + timedelta(days=365),
        )
        self._records.append(record)
        return record

    def withdraw(self, subject: str, purpose: ConsentPurpose) -> ConsentRecord:
        """Record consent being withdrawn.

        Creates a new ConsentRecord with granted=False. Withdrawal
        takes effect immediately and has no expiry.
        """
        record = ConsentRecord(
            subject_email=subject,
            purpose=purpose,
            granted=False,
            timestamp=datetime.utcnow(),
            expiry_date=None,
        )
        self._records.append(record)
        return record

    def check(self, subject: str, purpose: ConsentPurpose) -> bool:
        """Check if consent is currently active for a subject and purpose.

        Returns True only if the latest record for this (subject, purpose)
        pair has granted=True and hasn't expired. The latest record is
        determined by insertion order (last appended wins on equal timestamps).
        """
        latest = None
        for record in self._records:
            if record.subject_email == subject and record.purpose == purpose:
                if latest is None or record.timestamp >= latest.timestamp:
                    latest = record

        if latest is None or not latest.granted:
            return False

        # Check expiry
        if latest.expiry_date and datetime.utcnow() > latest.expiry_date:
            return False

        return True

    def get_all(self, subject: str) -> list:
        """Get all consent records for a data subject.

        Returns the full history, not just current status.
        """
        return [r for r in self._records if r.subject_email == subject]


class DataSubjectRight(Enum):
    """GDPR data subject rights.

    Each right must be fulfilled within 30 calendar days of the request.
    """

    ACCESS = "access"
    ERASURE = "erasure"
    PORTABILITY = "portability"
    RECTIFICATION = "rectification"
    RESTRICTION = "restriction"
    OBJECTION = "objection"


@dataclass
class SubjectRequest:
    """A data subject rights request.

    Tracks the lifecycle of a GDPR request from submission through
    processing to completion, with deadline tracking.
    """

    id: str
    right: DataSubjectRight
    subject_email: str
    status: str  # "pending", "processing", "completed"
    submitted_at: datetime
    due_date: datetime
    completed_at: datetime = None


class DataSubjectRightsManager:
    """Manage data subject rights requests per GDPR requirements.

    Handles the lifecycle of access, erasure, portability, and other
    requests with automatic 30-day deadline calculation and overdue
    detection.
    """

    def __init__(self):
        self._requests: dict = {}

    def submit_request(self, subject: str, right: DataSubjectRight) -> SubjectRequest:
        """Create a new data subject request with a 30-day due date.

        Generates a unique ID and sets the deadline to 30 calendar days
        from submission.
        """
        now = datetime.utcnow()
        request = SubjectRequest(
            id=str(uuid.uuid4())[:8],
            right=right,
            subject_email=subject,
            status="pending",
            submitted_at=now,
            due_date=now + timedelta(days=30),
        )
        self._requests[request.id] = request
        return request

    def process_request(self, request_id: str) -> SubjectRequest:
        """Mark a request as being processed.

        Transitions status from 'pending' to 'processing'.
        """
        request = self._requests.get(request_id)
        if request is None:
            raise KeyError(f"Request {request_id} not found")
        request.status = "processing"
        return request

    def complete_request(self, request_id: str) -> SubjectRequest:
        """Mark a request as completed.

        Sets status to 'completed' and records the completion timestamp.
        """
        request = self._requests.get(request_id)
        if request is None:
            raise KeyError(f"Request {request_id} not found")
        request.status = "completed"
        request.completed_at = datetime.utcnow()
        return request

    def is_overdue(self, request_id: str) -> bool:
        """Check if a request has passed its due date without completion.

        Returns True if the request is not completed and current time
        exceeds the due date.
        """
        request = self._requests.get(request_id)
        if request is None:
            raise KeyError(f"Request {request_id} not found")
        if request.status == "completed":
            return False
        return datetime.utcnow() > request.due_date


class RetentionPolicy:
    """Data retention policy with configurable per-category rules.

    Enforces data lifecycle by determining when data should be purged
    based on its category and creation date.
    """

    def __init__(self, default_retention_days: int = 365):
        """Initialize with a default retention period.

        Args:
            default_retention_days: days to retain data if no category-specific rule exists
        """
        self._default_days = default_retention_days
        self._rules: dict = {}

    def add_rule(self, data_category: str, retention_days: int) -> None:
        """Add a retention rule for a specific data category.

        Args:
            data_category: e.g., "trip_data", "payment_logs", "analytics"
            retention_days: how long to keep data in this category
        """
        self._rules[data_category] = retention_days

    def should_purge(self, data_category: str, created_date: datetime) -> bool:
        """Check if data in this category should be purged.

        Uses the category-specific rule if available, otherwise the default.
        """
        retention_days = self._rules.get(data_category, self._default_days)
        cutoff = datetime.utcnow() - timedelta(days=retention_days)
        return created_date < cutoff

    def get_purgeable(self, data_categories_with_dates: list) -> list:
        """Identify all data items that should be purged.

        Args:
            data_categories_with_dates: list of (category, created_date) tuples

        Returns:
            list of (category, created_date) tuples that should be purged
        """
        return [
            (cat, date) for cat, date in data_categories_with_dates
            if self.should_purge(cat, date)
        ]
