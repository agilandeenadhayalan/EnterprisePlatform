"""Fare split service repository."""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from models import FareSplitModel, FareSplitParticipantModel

class FareSplitRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_split(self, trip_id: str, initiator_id: str, total_amount: float) -> FareSplitModel:
        split = FareSplitModel(trip_id=trip_id, initiator_id=initiator_id, total_amount=total_amount)
        self.db.add(split)
        await self.db.flush()
        return split

    async def add_participant(self, split_id: str, user_id: str, share_amount: float) -> FareSplitParticipantModel:
        participant = FareSplitParticipantModel(split_id=split_id, user_id=user_id, share_amount=share_amount)
        self.db.add(participant)
        await self.db.flush()
        return participant

    async def get_split_by_id(self, split_id: str) -> Optional[FareSplitModel]:
        result = await self.db.execute(select(FareSplitModel).where(FareSplitModel.id == split_id))
        return result.scalar_one_or_none()

    async def get_split_by_trip(self, trip_id: str) -> Optional[FareSplitModel]:
        result = await self.db.execute(select(FareSplitModel).where(FareSplitModel.trip_id == trip_id))
        return result.scalar_one_or_none()

    async def get_participants(self, split_id: str) -> list[FareSplitParticipantModel]:
        result = await self.db.execute(
            select(FareSplitParticipantModel).where(FareSplitParticipantModel.split_id == split_id)
        )
        return list(result.scalars().all())

    async def accept_split(self, split_id: str, user_id: str) -> bool:
        result = await self.db.execute(
            update(FareSplitParticipantModel)
            .where(FareSplitParticipantModel.split_id == split_id, FareSplitParticipantModel.user_id == user_id)
            .values(status="accepted")
        )
        return result.rowcount > 0
