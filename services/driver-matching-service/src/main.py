"""
Driver Matching Service — FastAPI application.

ROUTES:
  POST /match               — Find best driver candidates for a trip
  GET  /candidates/{trip_id} — Get cached match results for a trip
  GET  /health              — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Add project root for mobility-common imports
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
# Add service src for local imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app
from mobility_common.fastapi.errors import not_found
from mobility_common.kafka import EventProducer, Topics
from mobility_common.events import Event

import config as service_config
import schemas
import repository


@asynccontextmanager
async def lifespan(app):
    """Startup: create Kafka producer. No DB for stateless service."""
    producer = EventProducer(
        bootstrap_servers=service_config.settings.kafka_bootstrap_servers,
        client_id=service_config.settings.service_name,
    )
    await producer.start()
    app.state.producer = producer
    yield
    await producer.stop()


app = create_app(
    title="Driver Matching Service",
    version="0.1.0",
    description="Stateless driver-trip matching and scoring engine",
    lifespan=lifespan,
)


# -- Routes --


@app.post("/match", response_model=schemas.MatchResponse)
async def match_drivers(body: schemas.MatchRequest):
    """
    Find the best driver candidates for a trip.

    Scores each candidate based on distance, rating, and acceptance rate,
    then returns ranked results.
    """
    result = repository.match_drivers(body)
    repository.cache_match_result(body.trip_id, result)

    # Publish matching event if a match was found
    if result.best_match:
        event = Event(
            event_type="driver.matching.completed",
            source=service_config.settings.service_name,
            correlation_id=body.trip_id,
            payload={
                "trip_id": body.trip_id,
                "best_driver_id": result.best_match.driver_id,
                "best_score": result.best_match.score,
                "total_eligible": result.total_eligible,
            },
        )
        await app.state.producer.send_event(Topics.DRIVER_MATCHING, event)

    return result


@app.get("/candidates/{trip_id}", response_model=schemas.CandidatesResponse)
async def get_candidates(trip_id: str):
    """Get cached match results for a trip."""
    cached = repository.get_cached_result(trip_id)
    if not cached:
        raise not_found("Match result", trip_id)
    return schemas.CandidatesResponse(
        trip_id=trip_id,
        candidates=cached.candidates,
        total=len(cached.candidates),
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=service_config.settings.service_port,
        reload=service_config.settings.debug,
    )
