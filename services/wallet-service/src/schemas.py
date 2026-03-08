"""Pydantic schemas for the wallet service API."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class TopupRequest(BaseModel):
    amount: float = Field(..., gt=0)
    description: Optional[str] = None

class DebitRequest(BaseModel):
    amount: float = Field(..., gt=0)
    description: Optional[str] = None

class WalletResponse(BaseModel):
    id: str
    user_id: str
    balance: float
    currency: str
    created_at: datetime
    updated_at: datetime

class WalletTransactionResponse(BaseModel):
    id: str
    wallet_id: str
    user_id: str
    transaction_type: str
    amount: float
    balance_after: float
    description: Optional[str] = None
    created_at: datetime

class TransactionListResponse(BaseModel):
    transactions: list[WalletTransactionResponse]
    count: int
