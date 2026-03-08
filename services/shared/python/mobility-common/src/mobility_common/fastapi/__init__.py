"""
Shared FastAPI utilities for all Python microservices.

Every FastAPI service in the platform imports from here to get:
- App factory with standard middleware (CORS, error handling, health check)
- JWT authentication dependency
- RBAC permission checker
- Async database session management
- Cursor-based pagination
- RFC 7807 error responses
"""

from mobility_common.fastapi.app import create_app
from mobility_common.fastapi.database import get_db, create_engine_and_session
from mobility_common.fastapi.errors import ProblemDetail, problem_exception_handler
from mobility_common.fastapi.middleware import require_auth, require_role, get_current_user
from mobility_common.fastapi.pagination import PaginatedResponse, paginate

__all__ = [
    "create_app",
    "get_db",
    "create_engine_and_session",
    "ProblemDetail",
    "problem_exception_handler",
    "require_auth",
    "require_role",
    "get_current_user",
    "PaginatedResponse",
    "paginate",
]
