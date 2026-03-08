"""Tests for Module 03: RESTful API Design."""

from learning.phase_1.src.m03_rest_api_design.rest import (
    CursorPaginator,
    IdempotencyStore,
    not_found,
    validation_error,
)


class TestCursorPaginator:
    def test_first_page(self):
        items = [{"id": f"item-{i}"} for i in range(25)]
        paginator = CursorPaginator(items, page_size=10)
        page = paginator.get_page()
        assert len(page.items) == 10
        assert page.has_more is True
        assert page.next_cursor is not None

    def test_last_page(self):
        items = [{"id": f"item-{i}"} for i in range(5)]
        paginator = CursorPaginator(items, page_size=10)
        page = paginator.get_page()
        assert len(page.items) == 5
        assert page.has_more is False

    def test_cursor_continuation(self):
        items = [{"id": f"item-{i:02d}"} for i in range(15)]
        paginator = CursorPaginator(items, page_size=10)
        page1 = paginator.get_page()
        page2 = paginator.get_page(page1.next_cursor)
        assert len(page2.items) == 5
        assert page2.has_more is False


class TestIdempotencyStore:
    def test_first_call_executes(self):
        store = IdempotencyStore()
        result = store.get_or_execute("key-1", lambda: {"status": "ok"})
        assert result["_idempotent_replay"] is False

    def test_retry_returns_cached(self):
        store = IdempotencyStore()
        store.get_or_execute("key-1", lambda: {"status": "ok"})
        result = store.get_or_execute("key-1", lambda: {"status": "different"})
        assert result["_idempotent_replay"] is True
        assert result["status"] == "ok"


class TestProblemDetails:
    def test_not_found(self):
        err = not_found("trip", "trip-999")
        assert err.status == 404
        assert "trip-999" in err.detail

    def test_validation_error(self):
        err = validation_error("email", "invalid format")
        assert err.status == 422
