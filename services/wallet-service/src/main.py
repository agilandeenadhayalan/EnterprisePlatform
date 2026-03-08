"""
Wallet Service — FastAPI application.

ROUTES:
  GET  /wallets/{user_id}              — Get wallet balance
  POST /wallets/{user_id}/topup        — Add funds to wallet
  POST /wallets/{user_id}/debit        — Deduct funds from wallet
  GET  /wallets/{user_id}/transactions — List wallet transactions
  GET  /health                         — Health check
"""
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app
from mobility_common.fastapi.database import create_engine_and_session, get_db, dispose_engine
from mobility_common.fastapi.errors import not_found, validation_error
import config as wallet_config
import models  # noqa: F401
import schemas
import repository

@asynccontextmanager
async def lifespan(app):
    create_engine_and_session(wallet_config.settings.database_url)
    yield
    await dispose_engine()

app = create_app(title="Wallet Service", version="0.1.0",
    description="Digital wallet management for Smart Mobility Platform", lifespan=lifespan)

def _wallet_response(w) -> schemas.WalletResponse:
    return schemas.WalletResponse(id=str(w.id), user_id=str(w.user_id), balance=w.balance,
        currency=w.currency, created_at=w.created_at, updated_at=w.updated_at)

def _txn_response(t) -> schemas.WalletTransactionResponse:
    return schemas.WalletTransactionResponse(id=str(t.id), wallet_id=str(t.wallet_id),
        user_id=str(t.user_id), transaction_type=t.transaction_type,
        amount=t.amount, balance_after=t.balance_after, description=t.description,
        created_at=t.created_at)

@app.get("/wallets/{user_id}", response_model=schemas.WalletResponse)
async def get_wallet(user_id: str, db: AsyncSession = Depends(get_db)):
    repo = repository.WalletRepository(db)
    wallet = await repo.get_wallet(user_id)
    if not wallet:
        # Auto-create wallet for new users
        wallet = await repo.create_wallet(user_id)
    return _wallet_response(wallet)

@app.post("/wallets/{user_id}/topup", response_model=schemas.WalletTransactionResponse)
async def topup_wallet(user_id: str, body: schemas.TopupRequest, db: AsyncSession = Depends(get_db)):
    repo = repository.WalletRepository(db)
    wallet = await repo.get_wallet(user_id)
    if not wallet:
        wallet = await repo.create_wallet(user_id)

    new_balance = wallet.balance + body.amount
    await repo.update_balance(user_id, new_balance)
    txn = await repo.create_transaction(
        wallet_id=str(wallet.id), user_id=user_id, transaction_type="topup",
        amount=body.amount, balance_after=new_balance, description=body.description,
    )
    return _txn_response(txn)

@app.post("/wallets/{user_id}/debit", response_model=schemas.WalletTransactionResponse)
async def debit_wallet(user_id: str, body: schemas.DebitRequest, db: AsyncSession = Depends(get_db)):
    repo = repository.WalletRepository(db)
    wallet = await repo.get_wallet(user_id)
    if not wallet:
        raise not_found("Wallet", user_id)
    if wallet.balance < body.amount:
        raise validation_error("Insufficient wallet balance")

    new_balance = wallet.balance - body.amount
    await repo.update_balance(user_id, new_balance)
    txn = await repo.create_transaction(
        wallet_id=str(wallet.id), user_id=user_id, transaction_type="debit",
        amount=body.amount, balance_after=new_balance, description=body.description,
    )
    return _txn_response(txn)

@app.get("/wallets/{user_id}/transactions", response_model=schemas.TransactionListResponse)
async def list_transactions(user_id: str, db: AsyncSession = Depends(get_db)):
    repo = repository.WalletRepository(db)
    txns = await repo.list_transactions(user_id)
    return schemas.TransactionListResponse(transactions=[_txn_response(t) for t in txns], count=len(txns))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=wallet_config.settings.service_port, reload=wallet_config.settings.debug)
