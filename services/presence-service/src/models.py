"""
Presence service models — no database tables.

Presence data is stored in Redis with TTL-based expiration.
When a heartbeat expires, the user is considered offline.
"""
