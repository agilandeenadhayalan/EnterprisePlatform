"""
RFC 7807 Problem Details error handling.

WHY RFC 7807? Without a standard error format, every service invents its own:
  - Service A: {"error": "not found"}
  - Service B: {"message": "Not Found", "code": 404}
  - Service C: {"errors": [{"msg": "Not Found"}]}

RFC 7807 (https://tools.ietf.org/html/rfc7807) defines a machine-readable
format that all services agree on. The API gateway and frontends can parse
errors consistently regardless of which backend produced them.

STRUCTURE:
  {
    "type": "https://api.mobility.dev/errors/not-found",
    "title": "Resource Not Found",
    "status": 404,
    "detail": "User with id 'abc-123' does not exist",
    "instance": "/api/v1/users/abc-123"
  }
"""

from typing import Any, Optional

from fastapi import Request
from fastapi.responses import JSONResponse


class ProblemDetail(Exception):
    """
    Exception that produces an RFC 7807 Problem Details response.

    Raise this anywhere in your route handlers and the global exception
    handler will convert it to a properly formatted JSON response.

    Usage:
        raise ProblemDetail(
            status=404,
            title="User Not Found",
            detail=f"No user with id '{user_id}'",
        )
    """

    def __init__(
        self,
        status: int,
        title: str,
        detail: Optional[str] = None,
        type_uri: Optional[str] = None,
        instance: Optional[str] = None,
        extensions: Optional[dict[str, Any]] = None,
    ):
        self.status = status
        self.title = title
        self.detail = detail
        self.type_uri = type_uri or "about:blank"
        self.instance = instance
        self.extensions = extensions or {}
        super().__init__(detail or title)


async def problem_exception_handler(request: Request, exc: ProblemDetail) -> JSONResponse:
    """Convert ProblemDetail exceptions into RFC 7807 JSON responses."""
    body: dict[str, Any] = {
        "type": exc.type_uri,
        "title": exc.title,
        "status": exc.status,
    }
    if exc.detail:
        body["detail"] = exc.detail
    if exc.instance:
        body["instance"] = exc.instance
    # Extensions go at the top level per RFC 7807
    body.update(exc.extensions)

    return JSONResponse(
        status_code=exc.status,
        content=body,
        media_type="application/problem+json",
    )


# ── Convenience factories ──

def not_found(resource: str, resource_id: str) -> ProblemDetail:
    """Create a 404 ProblemDetail for a missing resource."""
    return ProblemDetail(
        status=404,
        title=f"{resource} Not Found",
        detail=f"{resource} with id '{resource_id}' does not exist",
    )


def validation_error(detail: str, errors: Optional[list[dict]] = None) -> ProblemDetail:
    """Create a 422 ProblemDetail for validation failures."""
    return ProblemDetail(
        status=422,
        title="Validation Error",
        detail=detail,
        extensions={"errors": errors} if errors else {},
    )


def conflict(detail: str) -> ProblemDetail:
    """Create a 409 ProblemDetail for conflicts (e.g., duplicate email)."""
    return ProblemDetail(
        status=409,
        title="Conflict",
        detail=detail,
    )


def unauthorized(detail: str = "Authentication required") -> ProblemDetail:
    """Create a 401 ProblemDetail for missing/invalid credentials."""
    return ProblemDetail(
        status=401,
        title="Unauthorized",
        detail=detail,
    )


def forbidden(detail: str = "Insufficient permissions") -> ProblemDetail:
    """Create a 403 ProblemDetail for insufficient permissions."""
    return ProblemDetail(
        status=403,
        title="Forbidden",
        detail=detail,
    )
