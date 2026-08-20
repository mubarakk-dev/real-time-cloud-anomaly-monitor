from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Real-Time Cloud Anomaly Monitor"
    environment: str = "development"
    log_level: str = "INFO"
    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "postgresql+asyncpg://anomaly:anomaly@localhost:5432/anomaly_monitor"
    model_artifact: str = "models/window_random_forest.joblib"
    ingest_api_key: str = "change-me"
    stream_name: str = "telemetry:events"
    consumer_group: str = "anomaly-workers"
    prediction_channel: str = "predictions:live"
    prediction_retention: int = 1000
    allowed_lateness_seconds: int = 5
    worker_metrics_port: int = 9101


@lru_cache
def get_settings() -> Settings:
    return Settings()
