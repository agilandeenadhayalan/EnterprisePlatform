"""
Cursor-based pagination for list endpoints.

WHY cursor pagination instead of offset/limit?

Offset pagination (page=3&size=20 → OFFSET 40 LIMIT 20) has a critical flaw:
if new rows are inserted between page requests, items shift and users see
duplicates or miss items. At scale (1B+ trips), OFFSET 1000000 also forces
PostgreSQL to scan and discard 1M rows.

Cursor pagination uses a stable pointer (the last item's ID or timestamp):
  "Give me 20 items after cursor=abc-123"
This is:
- Consistent: inserts don't cause duplicates
- Fast: uses indexed WHERE id > cursor LIMIT 20 (always O(1) index lookup)
- Stateless: no server-side page tracking needed

TRADE-OFF: You can't jump to "page 47" — only next/previous. This is fine for
infinite scroll and API consumption, but poor for admin dashboards (use offset
there, or add a search/filter instead).
"""

import base64
from typing import Any, Generic, Optional, Sequence, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response wrapper."""
    items: list[Any]          # The actual data
    next_cursor: Optional[str] = None  # Pass this to get the next page
    has_more: bool = False    # True if more pages exist
    total_count: Optional[int] = None  # Optional: total matching items


def encode_cursor(value: str) -> str:
    """Encode a cursor value to an opaque base64 string."""
    return base64.urlsafe_b64encode(value.encode()).decode()


def decode_cursor(cursor: str) -> str:
    """Decode a base64 cursor back to the original value."""
    try:
        return base64.urlsafe_b64decode(cursor.encode()).decode()
    except Exception:
        return cursor


def paginate(
    items: Sequence[Any],
    limit: int,
    cursor_field: str = "id",
) -> PaginatedResponse:
    """
    Build a PaginatedResponse from a list of items.

    The caller should query limit+1 items from the database. If we get
    limit+1 back, there are more pages; we return only `limit` items
    and set the cursor to the last returned item's ID.

    Args:
        items: Query results (should be limit+1 items if more exist)
        limit: Requested page size
        cursor_field: Which field to use as the cursor (default: "id")

    Returns:
        PaginatedResponse with items, next_cursor, and has_more
    """
    has_more = len(items) > limit
    page_items = list(items[:limit])

    next_cursor = None
    if has_more and page_items:
        last_item = page_items[-1]
        # Support both dict and object attribute access
        if isinstance(last_item, dict):
            cursor_value = str(last_item[cursor_field])
        else:
            cursor_value = str(getattr(last_item, cursor_field))
        next_cursor = encode_cursor(cursor_value)

    return PaginatedResponse(
        items=page_items,
        next_cursor=next_cursor,
        has_more=has_more,
    )
