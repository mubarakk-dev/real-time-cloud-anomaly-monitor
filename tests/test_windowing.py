from datetime import UTC, datetime, timedelta

import fakeredis.aioredis
import pytest

from app.schemas import TelemetryEvent
from app.windowing import claim_completed_windows, update_window


@pytest.mark.asyncio
async def test_redis_window_aggregation_matches_feature_contract():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    start = datetime(2026, 1, 1, tzinfo=UTC)
    first = TelemetryEvent(
        timestamp=start,
        service="payment-service",
        event_type="payment",
        response_time_ms=100,
        cpu_usage=20,
        memory_usage=40,
        status_code=200,
        log_level="INFO",
    )
    second = first.model_copy(
        update={
            "timestamp": start + timedelta(seconds=1),
            "response_time_ms": 300,
            "cpu_usage": 60,
            "memory_usage": 80,
            "status_code": 500,
            "log_level": "ERROR",
        }
    )
    await update_window(redis, first, 30)
    await update_window(redis, second, 30)
    windows = await claim_completed_windows(redis, start + timedelta(seconds=30))
    assert len(windows) == 1
    window = windows[0]
    assert window["service"] == "payment-service"
    assert window["avg_response_time"] == 200
    assert window["max_response_time"] == 300
    assert window["avg_cpu_usage"] == 40
    assert window["avg_memory_usage"] == 60
    assert window["error_rate"] == 0.5
    assert window["error_log_rate"] == 0.5
    assert window["log_count"] == 2


@pytest.mark.asyncio
async def test_windows_are_isolated_by_service():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    start = datetime(2026, 1, 1, tzinfo=UTC)
    for service in ("api-gateway", "database-service"):
        await update_window(
            redis,
            TelemetryEvent(
                timestamp=start,
                service=service,
                event_type="request",
                response_time_ms=100,
                cpu_usage=20,
                memory_usage=40,
                status_code=200,
                log_level="INFO",
            ),
            30,
        )
    windows = await claim_completed_windows(redis, start + timedelta(seconds=30))
    assert {window["service"] for window in windows} == {"api-gateway", "database-service"}
