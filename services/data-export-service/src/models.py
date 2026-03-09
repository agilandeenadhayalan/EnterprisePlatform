"""
Domain models for the data export service.

Represents export jobs, export requests, and export formats.
"""

from datetime import datetime
from typing import Any, Optional


class ExportFormat:
    """Supported export format definition."""

    def __init__(
        self,
        format_id: str,
        name: str,
        description: str,
        content_type: str,
        extension: str,
    ):
        self.format_id = format_id
        self.name = name
        self.description = description
        self.content_type = content_type
        self.extension = extension

    def to_dict(self) -> dict:
        return {
            "format_id": self.format_id,
            "name": self.name,
            "description": self.description,
            "content_type": self.content_type,
            "extension": self.extension,
        }


class ExportJob:
    """An export job tracking record."""

    def __init__(
        self,
        id: str,
        query: str,
        format: str,
        destination: str,
        status: str,
        row_count: int = 0,
        file_size_bytes: int = 0,
        download_url: Optional[str] = None,
        error_message: Optional[str] = None,
        created_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
    ):
        self.id = id
        self.query = query
        self.format = format
        self.destination = destination
        self.status = status  # pending, running, completed, failed, cancelled
        self.row_count = row_count
        self.file_size_bytes = file_size_bytes
        self.download_url = download_url
        self.error_message = error_message
        self.created_at = created_at or datetime.utcnow()
        self.completed_at = completed_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "query": self.query,
            "format": self.format,
            "destination": self.destination,
            "status": self.status,
            "row_count": self.row_count,
            "file_size_bytes": self.file_size_bytes,
            "download_url": self.download_url,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
