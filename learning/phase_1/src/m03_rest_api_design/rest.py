"""
RESTful API Design Patterns Simulator
======================================

Demonstrates pagination, idempotency, and error handling patterns.
"""

from __future__ import annotations

import uuid
import hashlib
from dataclasses import dataclass, field
from typing import Any, Optional


# ── Pagination ──


@dataclass
class CursorPage:
    """
    Cursor-based pagination result.

    WHY cursor over offset:
    - Offset pagination breaks when data is inserted/deleted
    - Cursor is stable even with concurrent modifications
    - Better performance on large datasets (no OFFSET skip)
    - Used by: Stripe, Slack, GitHub, Twitter APIs

    TRADE-OFF: No "jump to page N" support (use offset for that).
    """
    items: list[Any]
    next_cursor: Optional[str] = None
    has_more: bool = False


class CursorPaginator:
    """Cursor-based pagination over an in-memory list."""

    def __init__(self, items: list[dict], page_size: int = 10) -> None:
        self.items = sorted(items, key=lambda x: x.get("id", ""))
        self.page_size = page_size

    def get_page(self, cursor: str | None = None) -> CursorPage:
        """Get a page of items starting after the cursor."""
        start_idx = 0
        if cursor:
            for i, item in enumerate(self.items):
                if str(item.get("id", "")) == cursor:
                    start_idx = i + 1
                    break

        end_idx = start_idx + self.page_size
        page_items = self.items[start_idx:end_idx]
        has_more = end_idx < len(self.items)
        next_cursor = str(page_items[-1]["id"]) if page_items and has_more else None

        return CursorPage(
            items=page_items,
            next_cursor=next_cursor,
            has_more=has_more,
        )


# ── Idempotency ──


class IdempotencyStore:
    """
    Idempotency key store for safe request retries.

    WHY: Network failures cause clients to retry requests. Without
    idempotency, retrying a payment could charge the user twice.

    HOW: Client sends a unique key with each request. Server stores
    the response and returns the cached result on retries.

    Used by: Stripe (Idempotency-Key header), PayPal, Square.
    """

    def __init__(self) -> None:
        self.store: dict[str, dict] = {}

    def get_or_execute(self, key: str, operation: callable) -> dict:
        """Return cached result or execute operation and cache."""
        if key in self.store:
            result = self.store[key]
            result["_idempotent_replay"] = True
            return result

        result = operation()
        result["_idempotent_replay"] = False
        self.store[key] = result
        return result


# ── RFC 7807 Problem Details ──


@dataclass
class ProblemDetail:
    """
    Standard error response following RFC 7807.

    WHY: Consistent error format across all 155 services.
    Every API returns the same error structure, making client
    error handling predictable.
    """
    type: str = "about:blank"
    title: str = "Internal Server Error"
    status: int = 500
    detail: str = ""
    instance: str = ""

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "title": self.title,
            "status": self.status,
            "detail": self.detail,
            "instance": self.instance,
        }


# Common error factory
def not_found(resource: str, resource_id: str) -> ProblemDetail:
    return ProblemDetail(
        type="/errors/not-found",
        title="Not Found",
        status=404,
        detail=f"{resource} with id '{resource_id}' not found",
        instance=f"/{resource}/{resource_id}",
    )


def validation_error(field: str, message: str) -> ProblemDetail:
    return ProblemDetail(
        type="/errors/validation",
        title="Validation Error",
        status=422,
        detail=f"Field '{field}': {message}",
    )
