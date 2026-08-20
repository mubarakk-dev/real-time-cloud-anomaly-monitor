import os
import random
from datetime import UTC, datetime

from locust import HttpUser, between, task


class TelemetryProducer(HttpUser):
    wait_time = between(0.05, 0.2)

    @task
    def ingest(self):
        self.client.post(
            "/v1/events",
            headers={"X-API-Key": os.getenv("INGEST_API_KEY", "change-me-before-deployment")},
            json={
                "timestamp": datetime.now(UTC).isoformat(),
                "service": random.choice(("api-gateway", "payment-service", "database-service")),
                "event_type": "request",
                "response_time_ms": random.uniform(100, 900),
                "cpu_usage": random.uniform(20, 95),
                "memory_usage": random.uniform(30, 90),
                "status_code": random.choice((200, 200, 200, 429, 500)),
                "log_level": random.choice(("INFO", "INFO", "WARN", "ERROR")),
            },
        )
