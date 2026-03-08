"""
Autocomplete service models — no database tables.

Autocomplete uses in-memory prefix matching data structures.
In production, this might be backed by Redis sorted sets or a trie.
"""
