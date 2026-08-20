from datetime import UTC, datetime, timedelta
from hashlib import sha1

from redis.asyncio import Redis
from redis.exceptions import WatchError

from .schemas import TelemetryEvent

ACTIVE_WINDOWS_KEY = "windows:active"


def _window_bounds(timestamp: datetime, window_seconds: int) -> tuple[datetime, datetime]:
    current = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=UTC)
    current = current.astimezone(UTC)
    epoch = int(current.timestamp())
    start_epoch = epoch - epoch % window_seconds
    start = datetime.fromtimestamp(start_epoch, tz=UTC)
    return start, start + timedelta(seconds=window_seconds)


def _window_key(service: str, start: datetime) -> str:
    service_hash = sha1(service.encode("utf-8"), usedforsecurity=False).hexdigest()[:12]
    return f"window:{int(start.timestamp())}:{service_hash}"


async def update_window(redis: Redis, event: TelemetryEvent, window_seconds: int) -> None:
    start, end = _window_bounds(event.timestamp, window_seconds)
    key = _window_key(event.service, start)
    while True:
        transaction = redis.pipeline(transaction=True)
        try:
            await transaction.watch(key)
            values = await transaction.hgetall(key)
            count = int(values.get("count", 0)) + 1
            mapping = {
                "service": event.service,
                "window_start": start.isoformat(),
                "window_end": end.isoformat(),
                "count": count,
                "response_sum": float(values.get("response_sum", 0)) + event.response_time_ms,
                "response_max": max(float(values.get("response_max", 0)), event.response_time_ms),
                "cpu_sum": float(values.get("cpu_sum", 0)) + event.cpu_usage,
                "cpu_max": max(float(values.get("cpu_max", 0)), event.cpu_usage),
                "memory_sum": float(values.get("memory_sum", 0)) + event.memory_usage,
                "memory_max": max(float(values.get("memory_max", 0)), event.memory_usage),
                "server_errors": int(values.get("server_errors", 0)) + int(event.status_code >= 500),
                "warnings": int(values.get("warnings", 0)) + int(event.log_level == "WARN"),
                "error_logs": int(values.get("error_logs", 0)) + int(event.log_level == "ERROR"),
            }
            transaction.multi()
            transaction.hset(key, mapping=mapping)
            transaction.expire(key, max(window_seconds * 10, 600))
            transaction.zadd(ACTIVE_WINDOWS_KEY, {key: end.timestamp()})
            await transaction.execute()
            break
        except WatchError:
            continue
        finally:
            await transaction.reset()


async def claim_completed_windows(redis: Redis, watermark: datetime) -> list[dict]:
    current = watermark if watermark.tzinfo else watermark.replace(tzinfo=UTC)
    keys = await redis.zrangebyscore(ACTIVE_WINDOWS_KEY, min=0, max=current.timestamp())
    completed: list[dict] = []
    for key in keys:
        lock_key = f"lock:{key}"
        if not await redis.set(lock_key, "1", nx=True, ex=30):
            continue
        values = await redis.hgetall(key)
        if values:
            completed.append(_to_features(values))
        transaction = redis.pipeline(transaction=True)
        transaction.delete(key)
        transaction.zrem(ACTIVE_WINDOWS_KEY, key)
        transaction.delete(lock_key)
        await transaction.execute()
    return completed


async def flush_windows(redis: Redis) -> list[dict]:
    return await claim_completed_windows(redis, datetime.max.replace(tzinfo=UTC))


def _to_features(values: dict[str, str]) -> dict:
    count = int(values["count"])
    return {
        "window_start": datetime.fromisoformat(values["window_start"]),
        "window_end": datetime.fromisoformat(values["window_end"]),
        "service": values["service"],
        "avg_response_time": float(values["response_sum"]) / count,
        "max_response_time": float(values["response_max"]),
        "avg_cpu_usage": float(values["cpu_sum"]) / count,
        "max_cpu_usage": float(values["cpu_max"]),
        "avg_memory_usage": float(values["memory_sum"]) / count,
        "max_memory_usage": float(values["memory_max"]),
        "error_rate": int(values["server_errors"]) / count,
        "warn_rate": int(values["warnings"]) / count,
        "error_log_rate": int(values["error_logs"]) / count,
        "log_count": count,
    }
