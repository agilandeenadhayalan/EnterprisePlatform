"""
Address service repository — database access layer.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models import AddressModel


class AddressRepository:
    """Database operations for the address service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_address(self, user_id: str, **fields) -> AddressModel:
        """Insert a new address record."""
        address = AddressModel(user_id=user_id, **fields)
        self.db.add(address)
        await self.db.flush()
        return address

    async def get_address_by_id(self, address_id: str) -> Optional[AddressModel]:
        """Find an address by its UUID."""
        result = await self.db.execute(
            select(AddressModel).where(AddressModel.id == address_id)
        )
        return result.scalar_one_or_none()

    async def list_user_addresses(self, user_id: str) -> list[AddressModel]:
        """List all addresses for a user, default address first."""
        result = await self.db.execute(
            select(AddressModel)
            .where(AddressModel.user_id == user_id)
            .order_by(AddressModel.is_default.desc(), AddressModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_address(self, address_id: str, **fields) -> Optional[AddressModel]:
        """Update specific fields on an address record."""
        await self.db.execute(
            update(AddressModel)
            .where(AddressModel.id == address_id)
            .values(**fields, updated_at=datetime.utcnow())
        )
        return await self.get_address_by_id(address_id)

    async def delete_address(self, address_id: str) -> bool:
        """Delete an address record. Returns True if a row was deleted."""
        result = await self.db.execute(
            delete(AddressModel).where(AddressModel.id == address_id)
        )
        return result.rowcount > 0

    async def clear_default(self, user_id: str) -> None:
        """Clear the is_default flag on all addresses for a user."""
        await self.db.execute(
            update(AddressModel)
            .where(AddressModel.user_id == user_id)
            .values(is_default=False, updated_at=datetime.utcnow())
        )

    async def set_default(self, address_id: str, user_id: str) -> Optional[AddressModel]:
        """
        Set an address as the default for a user.

        First clears is_default on all other addresses for this user,
        then sets is_default=True on the specified address.
        """
        await self.clear_default(user_id)
        return await self.update_address(address_id, is_default=True)
