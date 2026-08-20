import json
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Query, WebSocket, WebSocketDisconnect
from prometheus_client import make_asgi_app
from redis.asyncio import Redis

from .config import get_settings
from .database import database_ready, initialise_database
from .logging import configure_logging
from .metrics import EVENTS_ACCEPTED
from .repository import recent_predictions
from .schemas import IngestResponse, PredictionResponse, TelemetryEvent
from .security import require_api_key

settings = get_settings()
configure_logging(settings.log_level)
redis = Redis.from_url(settings.redis_url, decode_responses=True)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await initialise_database()
    await redis.ping()
    yield
    await redis.aclose()


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Containerised streaming anomaly monitoring for service telemetry.",
    lifespan=lifespan,
)
app.mount("/metrics", make_asgi_app())


@app.get("/")
async def root() -> dict:
    return {"service": settings.app_name, "docs": "/docs", "health": "/health"}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "environment": settings.environment}


@app.get("/ready")
async def ready() -> dict:
    await redis.ping()
    await database_ready()
    return {"status": "ready", "redis": "connected", "database": "connected"}


@app.post("/v1/events", response_model=IngestResponse, status_code=202, dependencies=[Depends(require_api_key)])
async def ingest(event: TelemetryEvent) -> IngestResponse:
    event_id = await redis.xadd(settings.stream_name, {"event": event.model_dump_json()})
    EVENTS_ACCEPTED.labels(service=event.service).inc()
    return IngestResponse(accepted=True, event_id=event_id)


@app.get("/v1/predictions", response_model=list[PredictionResponse])
async def predictions(limit: int = Query(100, ge=1, le=1000)):
    return await recent_predictions(limit=limit)


@app.get("/v1/alerts", response_model=list[PredictionResponse])
async def alerts(limit: int = Query(100, ge=1, le=1000)):
    return await recent_predictions(limit=limit, anomalies_only=True)


@app.websocket("/v1/live")
async def live_predictions(websocket: WebSocket) -> None:
    await websocket.accept()
    subscriber = redis.pubsub()
    await subscriber.subscribe(settings.prediction_channel)
    try:
        async for message in subscriber.listen():
            if message["type"] == "message":
                await websocket.send_json(json.loads(message["data"]))
    except WebSocketDisconnect:
        pass
    finally:
        await subscriber.unsubscribe(settings.prediction_channel)
        await subscriber.aclose()
