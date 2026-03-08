"""SQLAlchemy ORM models for the fare split service."""
from datetime import datetime
from sqlalchemy import DateTime, Float, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from mobility_common.fastapi.database import Base

class FareSplitModel(Base):
    __tablename__ = "fare_splits"
    __table_args__ = {"schema": "payments"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    trip_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    initiator_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")

class FareSplitParticipantModel(Base):
    __tablename__ = "fare_split_participants"
    __table_args__ = {"schema": "payments"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    split_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    share_amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
