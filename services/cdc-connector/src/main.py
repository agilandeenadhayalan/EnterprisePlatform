"""
CDC Connector Service

Change Data Capture service that polls PostgreSQL for changes using
updated_at columns. Publishes etl.cdc.events.v1 events to Kafka
and tracks per-table watermarks for incremental change capture.

Routes:
    GET    /cdc/status                      — Status of all CDC streams
    POST   /cdc/tables/{table_name}/sync    — Start CDC sync for a table
    GET    /cdc/tables                      — List tracked tables
    POST   /cdc/tables/{table_name}/register — Register a table for CDC
    DELETE /cdc/tables/{table_name}         — Stop tracking a table
    GET    /health                          — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import HTTPException

from mobility_common.fastapi.app import create_app

import config as service_config
import schemas
import repository
from models import CDCConfig


@asynccontextmanager
async def lifespan(app):
    yield


app = create_app(service_config.settings.service_name, lifespan=lifespan)
repo = repository.cdc_repo


def _tracker_to_response(tracker) -> schemas.TableTrackerResponse:
    return schemas.TableTrackerResponse(
        table_name=tracker.table_name,
        schema_name=tracker.schema_name,
        config=schemas.CDCConfigSchema(
            watermark_column=tracker.config.watermark_column,
            poll_interval_seconds=tracker.config.poll_interval_seconds,
            batch_size=tracker.config.batch_size,
            kafka_topic=tracker.config.kafka_topic,
        ),
        state=tracker.state.value,
        last_watermark=tracker.last_watermark,
        total_changes_captured=tracker.total_changes_captured,
        last_poll_at=tracker.last_poll_at,
        registered_at=tracker.registered_at,
    )


def _stream_to_response(stream) -> schemas.CDCStreamResponse:
    return schemas.CDCStreamResponse(
        table_name=stream.table_name,
        state=stream.state.value,
        events_captured=stream.events_captured,
        events_per_second=stream.events_per_second,
        last_event_at=stream.last_event_at,
        lag_seconds=stream.lag_seconds,
    )


@app.get("/cdc/status", response_model=schemas.CDCStatusResponse, tags=["CDC"])
async def cdc_status():
    """Get status of all CDC streams."""
    streams = repo.get_all_stream_statuses()
    return schemas.CDCStatusResponse(
        streams=[_stream_to_response(s) for s in streams],
        total_tables=len(streams),
        active_streams=repo.get_active_count(),
        total_events_captured=repo.get_total_events(),
    )


@app.post("/cdc/tables/{table_name}/sync", response_model=schemas.SyncResponse, tags=["CDC"])
async def sync_table(table_name: str):
    """Start a CDC sync for a registered table, capturing changes since last watermark."""
    if not repo.table_registered(table_name):
        raise HTTPException(
            status_code=404,
            detail=f"Table '{table_name}' is not registered for CDC. Use POST /cdc/tables/{table_name}/register first.",
        )

    changes_captured, events = repo.sync_table(table_name)
    tracker = repo.get_tracker(table_name)

    return schemas.SyncResponse(
        table_name=table_name,
        changes_captured=changes_captured,
        new_watermark=tracker.last_watermark,
        kafka_topic=tracker.config.kafka_topic,
        message=f"Captured {changes_captured} changes and published to {tracker.config.kafka_topic}",
    )


@app.get("/cdc/tables", response_model=schemas.TablesListResponse, tags=["CDC"])
async def list_tracked_tables():
    """List all tables registered for CDC tracking."""
    trackers = repo.get_all_trackers()
    return schemas.TablesListResponse(
        tables=[_tracker_to_response(t) for t in trackers],
        total=len(trackers),
    )


@app.post(
    "/cdc/tables/{table_name}/register",
    response_model=schemas.TableTrackerResponse,
    status_code=201,
    tags=["CDC"],
)
async def register_table(table_name: str, request: schemas.RegisterTableRequest = schemas.RegisterTableRequest()):
    """Register a table for CDC tracking."""
    if repo.table_registered(table_name):
        raise HTTPException(
            status_code=409,
            detail=f"Table '{table_name}' is already registered for CDC",
        )

    config = CDCConfig(
        watermark_column=request.config.watermark_column,
        poll_interval_seconds=request.config.poll_interval_seconds,
        batch_size=request.config.batch_size,
        kafka_topic=request.config.kafka_topic,
    )

    tracker = repo.register_table(
        table_name=table_name,
        schema_name=request.schema_name,
        config=config,
    )

    return _tracker_to_response(tracker)


@app.delete("/cdc/tables/{table_name}", status_code=204, tags=["CDC"])
async def unregister_table(table_name: str):
    """Stop tracking a table and remove its CDC registration."""
    if not repo.unregister_table(table_name):
        raise HTTPException(
            status_code=404,
            detail=f"Table '{table_name}' is not registered for CDC",
        )
