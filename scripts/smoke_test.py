"""End-to-end check for a running Docker Compose stack."""

import os
import time
from datetime import UTC, datetime, timedelta

import requests

API_URL = os.getenv("API_URL", "http://localhost:8000")
API_KEY = os.getenv("INGEST_API_KEY", "change-me-before-deployment")

requests.get(f"{API_URL}/ready", timeout=10).raise_for_status()
base = datetime.now(UTC) - timedelta(minutes=2)
for tick in range(40):
    event = {
        "timestamp": (base + timedelta(seconds=tick)).isoformat(),
        "service": "payment-service",
        "event_type": "payment",
        "response_time_ms": 900 if tick > 10 else 250,
        "cpu_usage": 90 if tick > 10 else 50,
        "memory_usage": 80,
        "status_code": 500 if tick > 10 else 200,
        "log_level": "ERROR" if tick > 10 else "INFO",
    }
    response = requests.post(
        f"{API_URL}/v1/events",
        json=event,
        headers={"X-API-Key": API_KEY},
        timeout=10,
    )
    response.raise_for_status()

for _ in range(20):
    predictions = requests.get(f"{API_URL}/v1/predictions", timeout=10).json()
    if predictions:
        print(f"End-to-end smoke test passed with {len(predictions)} persisted prediction(s).")
        break
    time.sleep(1)
else:
    raise RuntimeError("No predictions were persisted within 20 seconds.")
