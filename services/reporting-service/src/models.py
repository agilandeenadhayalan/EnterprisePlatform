"""
Domain models for the reporting service.

Represents reports, report requests, report results, and report types.
"""

from datetime import datetime
from typing import Any, Optional


class ReportType:
    """Definition of an available report type."""

    def __init__(
        self,
        type_id: str,
        name: str,
        description: str,
        required_params: list[str],
        optional_params: list[str],
        supported_formats: list[str],
    ):
        self.type_id = type_id
        self.name = name
        self.description = description
        self.required_params = required_params
        self.optional_params = optional_params
        self.supported_formats = supported_formats

    def to_dict(self) -> dict:
        return {
            "type_id": self.type_id,
            "name": self.name,
            "description": self.description,
            "required_params": self.required_params,
            "optional_params": self.optional_params,
            "supported_formats": self.supported_formats,
        }


class ReportResult:
    """The generated output of a report."""

    def __init__(
        self,
        summary: dict[str, Any],
        row_count: int,
        generated_at: Optional[str] = None,
    ):
        self.summary = summary
        self.row_count = row_count
        self.generated_at = generated_at or datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        return {
            "summary": self.summary,
            "row_count": self.row_count,
            "generated_at": self.generated_at,
        }


class Report:
    """A generated or pending report."""

    def __init__(
        self,
        id: str,
        report_type: str,
        status: str,
        parameters: dict[str, Any],
        format: str = "json",
        result: Optional[ReportResult] = None,
        created_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        error_message: Optional[str] = None,
    ):
        self.id = id
        self.report_type = report_type
        self.status = status  # pending, running, completed, failed
        self.parameters = parameters
        self.format = format
        self.result = result
        self.created_at = created_at or datetime.utcnow()
        self.completed_at = completed_at
        self.error_message = error_message

    def to_dict(self) -> dict:
        result = {
            "id": self.id,
            "report_type": self.report_type,
            "status": self.status,
            "parameters": self.parameters,
            "format": self.format,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "result": self.result.to_dict() if self.result else None,
        }
        return result
