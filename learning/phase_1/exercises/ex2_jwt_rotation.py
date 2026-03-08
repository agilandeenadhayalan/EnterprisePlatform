"""
Exercise 2: JWT Token Rotation
================================

Implement refresh token rotation — when a refresh token is used
to get a new access token, the old refresh token is invalidated
and a new one is issued.

WHY rotation:
- If a refresh token is stolen, rotation limits the damage window
- Each refresh token can only be used once
- Reuse of an old refresh token indicates theft → revoke all tokens

This is used by Auth0, Okta, and most modern auth providers.
"""

from learning.phase_1.src.m02_authentication.auth import JWTSimulator


class TokenRotator:
    """
    Refresh token rotation manager.

    On each token refresh:
    1. Validate the refresh token
    2. Issue new access + refresh tokens
    3. Invalidate the old refresh token
    4. If an already-used refresh token is presented → revoke ALL tokens for that user

    This creates a chain: RT1 → RT2 → RT3 → ...
    If RT1 is reused after RT2 was issued, it means RT1 was stolen.
    """

    def __init__(self) -> None:
        self.jwt = JWTSimulator()
        self.used_refresh_tokens: set[str] = set()     # Already-rotated tokens
        self.active_refresh_tokens: dict[str, str] = {} # user_id → current refresh jti

    def login(self, user_id: str, role: str) -> dict:
        """Issue initial token pair on login."""
        pair = self.jwt.create_token_pair(user_id, role)
        refresh_jti = pair["refresh_token"]["jti"]
        self.active_refresh_tokens[user_id] = refresh_jti
        return pair

    def refresh(self, refresh_token: str) -> dict | None:
        """
        Use a refresh token to get new tokens.

        Returns new token pair, or None if:
        - Token is invalid/expired
        - Token was already used (theft detected → revoke all)

        Steps:
        1. Validate the refresh token
        2. Check if it's in used_refresh_tokens (theft!)
        3. If theft: revoke all tokens for this user, return None
        4. Mark old refresh token as used
        5. Issue new token pair
        6. Update active_refresh_tokens for this user
        """
        # TODO: Implement this method (~15 lines)
        raise NotImplementedError("Implement token rotation")

    def _revoke_all_for_user(self, user_id: str) -> None:
        """Revoke all tokens for a user (nuclear option on theft detection)."""
        # TODO: Implement (~3 lines)
        raise NotImplementedError("Implement user token revocation")


# ── Tests ──


def test_login_returns_tokens():
    rotator = TokenRotator()
    tokens = rotator.login("user-1", "rider")
    assert "access_token" in tokens
    assert "refresh_token" in tokens


def test_refresh_issues_new_tokens():
    rotator = TokenRotator()
    tokens = rotator.login("user-1", "rider")
    new_tokens = rotator.refresh(tokens["refresh_token"]["token"])
    assert new_tokens is not None
    assert new_tokens["access_token"]["jti"] != tokens["access_token"]["jti"]


def test_reuse_detects_theft():
    rotator = TokenRotator()
    tokens = rotator.login("user-1", "rider")
    old_refresh = tokens["refresh_token"]["token"]

    # First refresh: works
    rotator.refresh(old_refresh)

    # Reuse old refresh token: theft detected!
    result = rotator.refresh(old_refresh)
    assert result is None
