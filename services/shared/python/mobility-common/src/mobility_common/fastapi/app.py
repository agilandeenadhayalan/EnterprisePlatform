"""
FastAPI app factory — creates a standard app with shared middleware.

WHY a factory? Every service needs the same boilerplate: CORS, error handling,
health check, JSON-formatted errors. By centralizing this, we:
1. Eliminate copy-paste across 13 Python services
2. Enforce consistent API behavior (same error format, same CORS policy)
3. Make platform-wide changes in one place (e.g., adding rate limiting later)

PATTERN: This is the "Application Factory" pattern, common in Flask (create_app)
and ASP.NET (WebApplication.CreateBuilder). FastAPI doesn't have a built-in
factory, so we create our own.
"""

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Callable, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from mobility_common.fastapi.errors import ProblemDetail, problem_exception_handler


def create_app(
    title: str,
    version: str = "0.1.0",
    description: str = "",
    lifespan: Optional[Callable] = None,
    **kwargs: Any,
) -> FastAPI:
    """
    Create a FastAPI app with standard platform middleware.

    Args:
        title: Service name (e.g., "Auth Service")
        version: API version
        description: OpenAPI description
        lifespan: Optional async context manager for startup/shutdown
        **kwargs: Additional FastAPI constructor arguments

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title=title,
        version=version,
        description=description,
        lifespan=lifespan,
        **kwargs,
    )

    # ── CORS ──
    # In development, allow all origins. In production, restrict to known domains.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Error handlers ──
    # Convert ProblemDetail exceptions into RFC 7807 JSON responses
    app.add_exception_handler(ProblemDetail, problem_exception_handler)

    # ── Health endpoint ──
    # Every service MUST expose /health for Docker health checks and
    # load balancer probes. This is the simplest possible implementation;
    # services can override with deeper checks (DB connectivity, etc.)
    @app.get("/health", tags=["Infrastructure"])
    async def health_check() -> dict:
        return {"status": "healthy", "service": title, "version": version}

    return app
