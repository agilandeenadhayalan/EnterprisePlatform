"""Wallet service repository."""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from models import WalletModel, WalletTransactionModel

class WalletRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_wallet(self, user_id: str) -> Optional[WalletModel]:
        result = await self.db.execute(select(WalletModel).where(WalletModel.user_id == user_id))
        return result.scalar_one_or_none()

    async def create_wallet(self, user_id: str, currency: str = "USD") -> WalletModel:
        wallet = WalletModel(user_id=user_id, currency=currency)
        self.db.add(wallet)
        await self.db.flush()
        return wallet

    async def update_balance(self, user_id: str, new_balance: float) -> Optional[WalletModel]:
        await self.db.execute(
            update(WalletModel).where(WalletModel.user_id == user_id)
            .values(balance=new_balance, updated_at=datetime.now(timezone.utc))
        )
        return await self.get_wallet(user_id)

    async def create_transaction(self, wallet_id: str, user_id: str,
        transaction_type: str, amount: float, balance_after: float,
        description: Optional[str] = None) -> WalletTransactionModel:
        txn = WalletTransactionModel(
            wallet_id=wallet_id, user_id=user_id, transaction_type=transaction_type,
            amount=amount, balance_after=balance_after, description=description,
        )
        self.db.add(txn)
        await self.db.flush()
        return txn

    async def list_transactions(self, user_id: str) -> list[WalletTransactionModel]:
        result = await self.db.execute(
            select(WalletTransactionModel).where(WalletTransactionModel.user_id == user_id)
            .order_by(WalletTransactionModel.created_at.desc())
        )
        return list(result.scalars().all())
