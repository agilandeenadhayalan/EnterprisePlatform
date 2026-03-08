"""
Push service models — no database tables.

Push notifications are sent via external providers (Firebase, APNs).
This service is stateless; delivery status is tracked in-memory or via Redis.
"""
