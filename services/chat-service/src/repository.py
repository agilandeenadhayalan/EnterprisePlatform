"""
Chat service repository — database access layer.
"""

from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import ChatRoomModel, ChatMessageModel


class ChatRepository:
    """Database operations for the chat service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_room(
        self,
        participant_ids: List[str],
        room_type: str = "trip",
        trip_id: Optional[str] = None,
    ) -> ChatRoomModel:
        """Create a new chat room."""
        room = ChatRoomModel(
            trip_id=trip_id,
            room_type=room_type,
            participant_ids=",".join(participant_ids),
        )
        self.db.add(room)
        await self.db.flush()
        return room

    async def get_room(self, room_id: str) -> Optional[ChatRoomModel]:
        """Get a chat room by ID."""
        result = await self.db.execute(
            select(ChatRoomModel).where(ChatRoomModel.id == room_id)
        )
        return result.scalar_one_or_none()

    async def get_room_by_trip(self, trip_id: str) -> Optional[ChatRoomModel]:
        """Get a chat room by trip ID."""
        result = await self.db.execute(
            select(ChatRoomModel).where(ChatRoomModel.trip_id == trip_id)
        )
        return result.scalar_one_or_none()

    async def send_message(
        self,
        room_id: str,
        sender_id: str,
        message: str,
        message_type: str = "text",
    ) -> ChatMessageModel:
        """Send a message to a chat room."""
        msg = ChatMessageModel(
            room_id=room_id,
            sender_id=sender_id,
            message=message,
            message_type=message_type,
        )
        self.db.add(msg)
        await self.db.flush()
        return msg

    async def get_room_messages(self, room_id: str, limit: int = 50) -> List[ChatMessageModel]:
        """Get messages for a chat room, ordered by most recent."""
        result = await self.db.execute(
            select(ChatMessageModel)
            .where(ChatMessageModel.room_id == room_id)
            .order_by(ChatMessageModel.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
