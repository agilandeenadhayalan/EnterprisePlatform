"""
Payment Service — FastAPI application.

ROUTES:
  POST  /payments            — Create a new payment
  GET   /payments/{id}       — Get payment details
  GET   /trips/{id}/payment  — Get payment for a trip
  PATCH /payments/{id}/status — Update payment status
  GET   /health              — Health check
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
from mobility_common.fastapi.errors import not_found
from mobility_common.kafka import EventProducer, Topics
from mobility_common.events import Event, EventTypes

import config as payment_config
import models  # noqa: F401
import schemas
import repository


@asynccontextmanager
async def lifespan(app):
    create_engine_and_session(payment_config.settings.database_url)
    producer = EventProducer(
        bootstrap_servers=payment_config.settings.kafka_bootstrap_servers,
        client_id="payment-service",
    )
    await producer.start()
    app.state.producer = producer
    yield
    await producer.stop()
    await dispose_engine()


app = create_app(
    title="Payment Service",
    version="0.1.0",
    description="Payment processing and tracking for Smart Mobility Platform",
    lifespan=lifespan,
)


def _to_response(p) -> schemas.PaymentResponse:
    return schemas.PaymentResponse(
        id=str(p.id), trip_id=str(p.trip_id), rider_id=str(p.rider_id),
        driver_id=str(p.driver_id) if p.driver_id else None,
        amount=p.amount, currency=p.currency,
        payment_method_id=str(p.payment_method_id) if p.payment_method_id else None,
        status=p.status, payment_gateway_ref=p.payment_gateway_ref,
        created_at=p.created_at, updated_at=p.updated_at,
    )


@app.post("/payments", response_model=schemas.PaymentResponse, status_code=201)
async def create_payment(body: schemas.CreatePaymentRequest, db: AsyncSession = Depends(get_db)):
    repo = repository.PaymentRepository(db)
    payment = await repo.create_payment(
        trip_id=body.trip_id, rider_id=body.rider_id, driver_id=body.driver_id,
        amount=body.amount, currency=body.currency, payment_method_id=body.payment_method_id,
    )

    event = Event(
        event_type=EventTypes.PAYMENT_INITIATED, source="payment-service",
        correlation_id=body.trip_id,
        payload={"payment_id": str(payment.id), "amount": body.amount, "trip_id": body.trip_id},
    )
    await app.state.producer.send_event(Topics.PAYMENT_EVENTS, event)

    return _to_response(payment)


@app.get("/payments/{payment_id}", response_model=schemas.PaymentResponse)
async def get_payment(payment_id: str, db: AsyncSession = Depends(get_db)):
    repo = repository.PaymentRepository(db)
    payment = await repo.get_by_id(payment_id)
    if not payment:
        raise not_found("Payment", payment_id)
    return _to_response(payment)


@app.get("/trips/{trip_id}/payment", response_model=schemas.PaymentResponse)
async def get_trip_payment(trip_id: str, db: AsyncSession = Depends(get_db)):
    repo = repository.PaymentRepository(db)
    payment = await repo.get_by_trip(trip_id)
    if not payment:
        raise not_found("Payment for trip", trip_id)
    return _to_response(payment)


@app.patch("/payments/{payment_id}/status", response_model=schemas.PaymentResponse)
async def update_payment_status(
    payment_id: str, body: schemas.UpdatePaymentStatusRequest,
    db: AsyncSession = Depends(get_db),
):
    repo = repository.PaymentRepository(db)
    payment = await repo.get_by_id(payment_id)
    if not payment:
        raise not_found("Payment", payment_id)

    updated = await repo.update_status(payment_id, body.status, body.payment_gateway_ref)

    event_type = EventTypes.PAYMENT_COMPLETED if body.status == "completed" else EventTypes.PAYMENT_FAILED
    if body.status in ("completed", "failed"):
        event = Event(
            event_type=event_type, source="payment-service",
            correlation_id=str(payment.trip_id),
            payload={"payment_id": payment_id, "status": body.status},
        )
        await app.state.producer.send_event(Topics.PAYMENT_EVENTS, event)

    return _to_response(updated)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=payment_config.settings.service_port, reload=payment_config.settings.debug)
