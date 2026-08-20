"""Generate realistic service telemetry and send it to the ingestion API."""

import argparse
import math
import os
import random
import time
from datetime import UTC, datetime

import requests

SERVICES = ("api-gateway", "auth-service", "payment-service", "inventory-service", "database-service", "cache-service")
EVENT_TYPES = ("request", "login", "payment", "inventory_check", "db_query", "cache_lookup")


def event_for(service: str, event_type: str, tick: int, rng: random.Random) -> dict:
    cycle = math.sin(2 * math.pi * tick / 300)
    latency = 250 + 30 * cycle + rng.gauss(0, 55)
    cpu = 50 + 8 * cycle + rng.gauss(0, 9)
    memory = 62 + rng.gauss(0, 7)
    status = rng.choices((200, 201, 400, 404, 429, 500, 503), weights=(70, 8, 7, 6, 4, 3, 2))[0]
    level = rng.choices(("INFO", "WARN", "ERROR"), weights=(84, 12, 4))[0]

    # A recurring service-local degradation makes the live alert path observable.
    if service == "payment-service" and tick % 240 in range(150, 205):
        latency += 420 + rng.gauss(0, 50)
        cpu += 28
        if rng.random() < 0.45:
            status = rng.choice((429, 500, 503))
            level = rng.choice(("WARN", "ERROR"))

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "service": service,
        "event_type": event_type,
        "response_time_ms": max(1, round(latency, 3)),
        "cpu_usage": min(100, max(0, round(cpu, 3))),
        "memory_usage": min(100, max(0, round(memory, 3))),
        "status_code": status,
        "log_level": level,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default=os.getenv("API_URL", "http://localhost:8000"))
    parser.add_argument("--api-key", default=os.getenv("INGEST_API_KEY", "change-me"))
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--continuous", action="store_true")
    parser.add_argument("--ticks", type=int, default=300)
    args = parser.parse_args()
    rng = random.Random(args.seed)
    tick = 0
    while args.continuous or tick < args.ticks:
        for service, event_type in zip(SERVICES, EVENT_TYPES, strict=True):
            response = requests.post(
                f"{args.api_url}/v1/events",
                json=event_for(service, event_type, tick, rng),
                headers={"X-API-Key": args.api_key},
                timeout=5,
            )
            response.raise_for_status()
        tick += 1
        if args.interval:
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
