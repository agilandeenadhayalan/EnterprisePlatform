"""
Presence Tracking
==================

Tracks online/offline status of users (drivers) using heartbeat signals
and timeout-based detection.

WHY presence tracking:
- Need to know which drivers are online and available for dispatch
- GPS updates serve as implicit heartbeats
- If a driver's app crashes, we need to detect they're offline
- Online count affects supply/demand calculations

Implementation:
- Each user sends periodic heartbeats (every N seconds)
- If no heartbeat received within timeout, user is marked offline
- Presence state: ONLINE, AWAY (stale heartbeat), OFFLINE (timed out)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class PresenceState(str, Enum):
    ONLINE = "online"
    AWAY = "away"       # Heartbeat stale but not timed out
    OFFLINE = "offline"


@dataclass
class UserPresence:
    """Presence record for a single user."""
    user_id: str
    state: PresenceState = PresenceState.OFFLINE
    last_heartbeat: float = 0.0
    metadata: dict[str, str] = field(default_factory=dict)

    def update_heartbeat(self, timestamp: float | None = None) -> None:
        """Record a heartbeat."""
        self.last_heartbeat = timestamp or time.time()
        self.state = PresenceState.ONLINE

    def seconds_since_heartbeat(self, now: float | None = None) -> float:
        """How long since the last heartbeat."""
        current = now or time.time()
        return current - self.last_heartbeat if self.last_heartbeat > 0 else float("inf")


class PresenceTracker:
    """
    Tracks online presence using heartbeats and timeouts.

    Users send periodic heartbeats. The tracker evaluates presence
    based on how long ago the last heartbeat was received.

    Thresholds:
    - ONLINE:  last heartbeat < away_timeout
    - AWAY:    away_timeout <= last heartbeat < offline_timeout
    - OFFLINE: last heartbeat >= offline_timeout
    """

    def __init__(
        self,
        away_timeout: float = 30.0,      # Seconds before "away"
        offline_timeout: float = 60.0,    # Seconds before "offline"
    ) -> None:
        self.away_timeout = away_timeout
        self.offline_timeout = offline_timeout
        self._users: dict[str, UserPresence] = {}

    def heartbeat(
        self,
        user_id: str,
        metadata: dict[str, str] | None = None,
        timestamp: float | None = None,
    ) -> UserPresence:
        """
        Record a heartbeat for a user.

        Creates the presence record if it doesn't exist.
        """
        if user_id not in self._users:
            self._users[user_id] = UserPresence(user_id=user_id)

        presence = self._users[user_id]
        presence.update_heartbeat(timestamp)
        if metadata:
            presence.metadata.update(metadata)

        return presence

    def get_presence(self, user_id: str, now: float | None = None) -> UserPresence:
        """Get the current presence state for a user."""
        if user_id not in self._users:
            return UserPresence(user_id=user_id, state=PresenceState.OFFLINE)

        presence = self._users[user_id]
        self._evaluate_state(presence, now)
        return presence

    def get_online_users(self, now: float | None = None) -> list[UserPresence]:
        """Get all users currently in ONLINE state."""
        self._evaluate_all(now)
        return [p for p in self._users.values() if p.state == PresenceState.ONLINE]

    def get_all_users(self, now: float | None = None) -> list[UserPresence]:
        """Get all tracked users with evaluated states."""
        self._evaluate_all(now)
        return list(self._users.values())

    def count_by_state(self, now: float | None = None) -> dict[PresenceState, int]:
        """Count users in each presence state."""
        self._evaluate_all(now)
        counts: dict[PresenceState, int] = {s: 0 for s in PresenceState}
        for presence in self._users.values():
            counts[presence.state] += 1
        return counts

    def remove_user(self, user_id: str) -> None:
        """Remove a user from presence tracking."""
        self._users.pop(user_id, None)

    def _evaluate_state(self, presence: UserPresence, now: float | None = None) -> None:
        """Evaluate and update a user's presence state based on heartbeat age."""
        elapsed = presence.seconds_since_heartbeat(now)

        if elapsed >= self.offline_timeout:
            presence.state = PresenceState.OFFLINE
        elif elapsed >= self.away_timeout:
            presence.state = PresenceState.AWAY
        else:
            presence.state = PresenceState.ONLINE

    def _evaluate_all(self, now: float | None = None) -> None:
        """Evaluate all users' states."""
        for presence in self._users.values():
            self._evaluate_state(presence, now)
