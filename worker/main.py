import asyncio
import json
import os
import socket
from datetime import UTC, datetime, timedelta

import structlog
from prometheus_client import start_http_server
from redis.asyncio import Redis
from redis.exceptions import ResponseError

from app.config import get_settings
from app.database import initialise_database
from app.logging import configure_logging
from app.metrics import ACTIVE_WINDOWS, EVENTS_PROCESSED, INFERENCE_TIME, PREDICTIONS, WORKER_ERRORS
from app.model import ModelRuntime
from app.repository import save_prediction
from app.schemas import PredictionResponse, TelemetryEvent
from app.windowing import ACTIVE_WINDOWS_KEY, claim_completed_windows, update_window

settings = get_settings()
configure_logging(settings.log_level)
log = structlog.get_logger()


async def ensure_group(redis: Redis) -> None:
    try:
        await redis.xgroup_create(settings.stream_name, settings.consumer_group, id="0", mkstream=True)
    except ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


async def publish_prediction(redis: Redis, runtime: ModelRuntime, window: dict) -> None:
    score, is_anomaly, elapsed_ms = runtime.predict(window)
    INFERENCE_TIME.observe(elapsed_ms / 1000)
    PREDICTIONS.labels(service=window["service"], outcome="anomaly" if is_anomaly else "normal").inc()
    stored = await save_prediction(
        {
            "window_start": window["window_start"],
            "window_end": window["window_end"],
            "service": window["service"],
            "anomaly_score": score,
            "threshold": runtime.threshold,
            "is_anomaly": is_anomaly,
            "inference_time_ms": elapsed_ms,
            "model_version": runtime.version,
        }
    )
    payload = PredictionResponse.model_validate(stored, from_attributes=True).model_dump(mode="json")
    await redis.publish(settings.prediction_channel, json.dumps(payload))
    await redis.lpush("predictions:recent", json.dumps(payload))
    await redis.ltrim("predictions:recent", 0, settings.prediction_retention - 1)
    log.info("window_classified", service=window["service"], score=score, anomaly=is_anomaly)


async def run() -> None:
    start_http_server(settings.worker_metrics_port)
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    runtime = ModelRuntime(settings.model_artifact)
    await initialise_database()
    await ensure_group(redis)
    consumer = f"{socket.gethostname()}-{os.getpid()}"
    max_seen = datetime.min.replace(tzinfo=UTC)
    log.info("worker_started", consumer=consumer, model_version=runtime.version)
    try:
        while True:
            batches = await redis.xreadgroup(
                settings.consumer_group,
                consumer,
                {settings.stream_name: ">"},
                count=100,
                block=5000,
            )
            for _, messages in batches:
                for event_id, fields in messages:
                    try:
                        event = TelemetryEvent.model_validate_json(fields["event"])
                        timestamp = event.timestamp if event.timestamp.tzinfo else event.timestamp.replace(tzinfo=UTC)
                        max_seen = max(max_seen, timestamp.astimezone(UTC))
                        await update_window(redis, event, runtime.window_seconds)
                        watermark = max_seen - timedelta(seconds=settings.allowed_lateness_seconds)
                        for window in await claim_completed_windows(redis, watermark):
                            await publish_prediction(redis, runtime, window)
                        EVENTS_PROCESSED.labels(service=event.service).inc()
                        ACTIVE_WINDOWS.set(await redis.zcard(ACTIVE_WINDOWS_KEY))
                        await redis.xack(settings.stream_name, settings.consumer_group, event_id)
                    except Exception as exc:  # event remains pending for operational recovery
                        WORKER_ERRORS.labels(exception=type(exc).__name__).inc()
                        log.exception("event_processing_failed", event_id=event_id)
            if not batches:
                await asyncio.sleep(0.05)
    finally:
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(run())
