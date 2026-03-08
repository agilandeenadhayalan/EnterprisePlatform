"""
Device service repository — database access layer.

Handles all SQL operations for device registration, lookup, trust management,
and removal. Each device is associated with a user via user_id.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models import DeviceModel


class DeviceRepository:
    """Database operations for the device service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_device(
        self,
        user_id: str,
        device_id: str,
        device_name: str,
        device_type: Optional[str] = None,
        os: Optional[str] = None,
        browser: Optional[str] = None,
        fingerprint: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> DeviceModel:
        """Register a new device for a user."""
        device = DeviceModel(
            user_id=user_id,
            device_id=device_id,
            device_name=device_name,
            device_type=device_type,
            os=os,
            browser=browser,
            fingerprint=fingerprint,
            ip_address=ip_address,
            last_used_at=datetime.utcnow(),
        )
        self.db.add(device)
        await self.db.flush()
        return device

    async def list_user_devices(self, user_id: str) -> list[DeviceModel]:
        """List all devices for a given user."""
        result = await self.db.execute(
            select(DeviceModel)
            .where(DeviceModel.user_id == user_id)
            .order_by(DeviceModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_device_by_id(self, device_pk: str) -> Optional[DeviceModel]:
        """Find a device by its primary key UUID."""
        result = await self.db.execute(
            select(DeviceModel).where(DeviceModel.id == device_pk)
        )
        return result.scalar_one_or_none()

    async def get_device_by_device_id(
        self, user_id: str, device_id: str
    ) -> Optional[DeviceModel]:
        """Find a device by its client-generated device_id for a specific user."""
        result = await self.db.execute(
            select(DeviceModel).where(
                DeviceModel.user_id == user_id,
                DeviceModel.device_id == device_id,
            )
        )
        return result.scalar_one_or_none()

    async def update_trust(self, device_pk: str, is_trusted: bool) -> Optional[DeviceModel]:
        """Toggle the trust status of a device."""
        await self.db.execute(
            update(DeviceModel)
            .where(DeviceModel.id == device_pk)
            .values(is_trusted=is_trusted, updated_at=datetime.utcnow())
        )
        return await self.get_device_by_id(device_pk)

    async def delete_device(self, device_pk: str) -> bool:
        """Remove a device. Returns True if a row was deleted."""
        result = await self.db.execute(
            delete(DeviceModel).where(DeviceModel.id == device_pk)
        )
        return result.rowcount > 0
