import fakeredis.aioredis
import pytest
from fastapi import HTTPException

from app import main
from app.schemas import TelemetryEvent
from app.security import require_api_key


def sample_event() -> TelemetryEvent:
    return TelemetryEvent.model_validate(
        {
            "timestamp": "2026-08-20T12:00:00Z",
            "service": "api-gateway",
            "event_type": "request",
            "response_time_ms": 220,
            "cpu_usage": 45,
            "memory_usage": 60,
            "status_code": 200,
            "log_level": "INFO",
        }
    )


@pytest.mark.asyncio
async def test_ingestion_appends_validated_event_to_redis_stream(monkeypatch):
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(main, "redis", fake_redis)
    response = await main.ingest(sample_event())
    assert response.accepted is True
    messages = await fake_redis.xrange(main.settings.stream_name)
    assert len(messages) == 1
    assert "anomaly_type" not in messages[0][1]["event"]


@pytest.mark.asyncio
async def test_ingestion_api_key_is_required():
    with pytest.raises(HTTPException) as error:
        await require_api_key("incorrect")
    assert error.value.status_code == 401
    assert await require_api_key("change-me") is None
