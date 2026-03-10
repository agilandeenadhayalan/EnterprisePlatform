"""
GDPR repository — in-memory data subject request and consent storage.

Manages DSRs, consent records, and audit trails.
"""

import uuid
from datetime import datetime
from typing import Optional

from models import DataSubjectRequest, ConsentRecord, RequestType, DSRStatus


class GDPRRepository:
    """In-memory GDPR data storage."""

    def __init__(self):
        self._requests: dict[str, DataSubjectRequest] = {}
        self._consent: dict[str, list[ConsentRecord]] = {}  # email -> list of consent records
        self._audit_trail: dict[str, list[dict]] = {}  # request_id -> list of audit entries

    # ── DSR CRUD ──

    def create_request(
        self,
        request_type: str,
        subject_email: str,
        data_categories: Optional[list[str]] = None,
        notes: Optional[str] = None,
    ) -> DataSubjectRequest:
        """Submit a new data subject request."""
        request_id = str(uuid.uuid4())
        dsr = DataSubjectRequest(
            id=request_id,
            request_type=request_type,
            subject_email=subject_email,
            data_categories=data_categories,
            notes=notes,
        )
        self._requests[request_id] = dsr
        self._audit_trail[request_id] = [
            {"action": "created", "timestamp": datetime.utcnow().isoformat(), "details": f"DSR {request_type} submitted"}
        ]
        return dsr

    def get_request(self, request_id: str) -> Optional[DataSubjectRequest]:
        """Get a DSR by ID."""
        return self._requests.get(request_id)

    def list_requests(
        self,
        request_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[DataSubjectRequest]:
        """List all DSRs, optionally filtered."""
        requests = list(self._requests.values())
        if request_type:
            requests = [r for r in requests if r.request_type == request_type]
        if status:
            requests = [r for r in requests if r.status == status]
        return requests

    def update_request(self, request_id: str, **fields) -> Optional[DataSubjectRequest]:
        """Update specific fields on a DSR."""
        dsr = self._requests.get(request_id)
        if not dsr:
            return None
        for key, value in fields.items():
            if value is not None and hasattr(dsr, key):
                setattr(dsr, key, value)
        # Add audit trail entry
        if request_id in self._audit_trail:
            self._audit_trail[request_id].append({
                "action": "updated",
                "timestamp": datetime.utcnow().isoformat(),
                "details": f"Fields updated: {', '.join(fields.keys())}",
            })
        return dsr

    def process_request(self, request_id: str) -> Optional[DataSubjectRequest]:
        """Process/execute a DSR."""
        dsr = self._requests.get(request_id)
        if not dsr:
            return None
        dsr.status = "processing"
        self._audit_trail.setdefault(request_id, []).append({
            "action": "processing_started",
            "timestamp": datetime.utcnow().isoformat(),
            "details": f"Processing {dsr.request_type} request for {dsr.subject_email}",
        })
        # Simulate processing completion
        dsr.status = "completed"
        dsr.completed_at = datetime.utcnow()
        self._audit_trail[request_id].append({
            "action": "completed",
            "timestamp": datetime.utcnow().isoformat(),
            "details": f"Request {dsr.request_type} completed successfully",
        })
        return dsr

    def get_audit_trail(self, request_id: str) -> Optional[list[dict]]:
        """Get audit trail for a DSR."""
        if request_id not in self._requests:
            return None
        return self._audit_trail.get(request_id, [])

    # ── Consent ──

    def record_consent(
        self,
        subject_email: str,
        purpose: str,
        granted: bool = True,
    ) -> ConsentRecord:
        """Record a consent grant or withdrawal."""
        consent_id = str(uuid.uuid4())
        record = ConsentRecord(
            id=consent_id,
            subject_email=subject_email,
            purpose=purpose,
            granted=granted,
        )
        self._consent.setdefault(subject_email, []).append(record)
        return record

    def get_consent_records(self, subject_email: str) -> list[ConsentRecord]:
        """Get all consent records for a data subject."""
        return self._consent.get(subject_email, [])


# Singleton repository instance
repo = GDPRRepository()
