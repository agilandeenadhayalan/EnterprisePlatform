"""
WebSocket gateway models — no database tables.

The WebSocket gateway is a stateless relay. Connection state
is managed in-memory; cross-instance coordination uses Redis pub/sub.
"""
