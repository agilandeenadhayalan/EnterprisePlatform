"""
Auth service repository — database access layer.

WHY a repository layer? Direct SQL in route handlers leads to:
1. Business logic mixed with data access (hard to test)
2. Duplicate queries across endpoints
3. No single place to add query optimizations

The repository pattern gives each service a clean API for data access.
Route handlers call repository methods; the repository handles SQL.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from auth_service.models import UserModel, SessionModel


class AuthRepository:
    """Database operations for the auth service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── User operations ──

    async def get_user_by_email(self, email: str) -> Optional[UserModel]:
        """Find a user by email address."""
        result = await self.db.execute(
            select(UserModel).where(UserModel.email == email)
        )
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: str) -> Optional[UserModel]:
        """Find a user by UUID."""
        result = await self.db.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_user(
        self,
        email: str,
        full_name: str,
        password_hash: str,
        phone: Optional[str] = None,
        role: str = "rider",
    ) -> UserModel:
        """Insert a new user and return the created record."""
        user = UserModel(
            email=email,
            full_name=full_name,
            password_hash=password_hash,
            phone=phone,
            role=role,
        )
        self.db.add(user)
        await self.db.flush()  # Populate server-generated fields (id, created_at)
        return user

    async def update_user(self, user_id: str, **fields) -> Optional[UserModel]:
        """Update specific fields on a user record."""
        await self.db.execute(
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(**fields, updated_at=datetime.utcnow())
        )
        return await self.get_user_by_id(user_id)

    # ── Session operations ──

    async def create_session(
        self,
        user_id: str,
        refresh_token: str,
        expires_at: datetime,
        device_info: Optional[dict] = None,
        ip_address: Optional[str] = None,
    ) -> SessionModel:
        """Store a refresh token as a session record."""
        session = SessionModel(
            user_id=user_id,
            refresh_token=refresh_token,
            expires_at=expires_at,
            device_info=device_info,
            ip_address=ip_address,
        )
        self.db.add(session)
        await self.db.flush()
        return session

    async def get_session_by_token(self, refresh_token: str) -> Optional[SessionModel]:
        """Find a session by its refresh token."""
        result = await self.db.execute(
            select(SessionModel).where(SessionModel.refresh_token == refresh_token)
        )
        return result.scalar_one_or_none()

    async def delete_session(self, session_id: str) -> None:
        """Revoke a specific session (logout from one device)."""
        await self.db.execute(
            delete(SessionModel).where(SessionModel.id == session_id)
        )

    async def delete_user_sessions(self, user_id: str) -> int:
        """Revoke all sessions for a user (logout everywhere)."""
        result = await self.db.execute(
            delete(SessionModel).where(SessionModel.user_id == user_id)
        )
        return result.rowcount
