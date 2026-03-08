"""
SMS service models — no database tables.

SMS messages are sent via external providers (Twilio, AWS SNS).
This service is stateless; delivery status is tracked in-memory.
"""
