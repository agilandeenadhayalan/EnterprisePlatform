"""
Driver document service repository — database access layer.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

import models


class DocumentRepository:
    """Database operations for the driver document service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_document(self, **fields) -> models.DriverDocumentModel:
        """Insert a new document record."""
        doc = models.DriverDocumentModel(**fields)
        self.db.add(doc)
        await self.db.flush()
        return doc

    async def get_document_by_id(self, document_id: str) -> Optional[models.DriverDocumentModel]:
        """Find a document by ID."""
        result = await self.db.execute(
            select(models.DriverDocumentModel)
            .where(models.DriverDocumentModel.id == document_id)
        )
        return result.scalar_one_or_none()

    async def get_driver_documents(
        self,
        driver_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> list[models.DriverDocumentModel]:
        """Get all documents for a driver."""
        result = await self.db.execute(
            select(models.DriverDocumentModel)
            .where(models.DriverDocumentModel.driver_id == driver_id)
            .order_by(models.DriverDocumentModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_driver_documents(self, driver_id: str) -> int:
        """Count total documents for a driver."""
        result = await self.db.execute(
            select(func.count())
            .select_from(models.DriverDocumentModel)
            .where(models.DriverDocumentModel.driver_id == driver_id)
        )
        return result.scalar() or 0

    async def verify_document(
        self,
        document_id: str,
        status: str,
        verified_by: str = None,
        rejection_reason: str = None,
    ) -> Optional[models.DriverDocumentModel]:
        """Update document verification status."""
        now = datetime.utcnow()
        update_fields = {
            "status": status,
            "updated_at": now,
        }
        if status == "verified":
            update_fields["verified_at"] = now
            if verified_by:
                update_fields["verified_by"] = verified_by
        elif status == "rejected" and rejection_reason:
            update_fields["rejection_reason"] = rejection_reason

        await self.db.execute(
            update(models.DriverDocumentModel)
            .where(models.DriverDocumentModel.id == document_id)
            .values(**update_fields)
        )
        return await self.get_document_by_id(document_id)
