from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TelemetryEvent(BaseModel):
    timestamp: datetime
    service: str = Field(min_length=1, max_length=100)
    event_type: str = Field(min_length=1, max_length=100)
    response_time_ms: float = Field(ge=0, le=120_000)
    cpu_usage: float = Field(ge=0, le=100)
    memory_usage: float = Field(ge=0, le=100)
    status_code: int = Field(ge=100, le=599)
    log_level: Literal["INFO", "WARN", "ERROR"]


class IngestResponse(BaseModel):
    accepted: bool
    event_id: str


class PredictionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    window_start: datetime
    window_end: datetime
    service: str
    anomaly_score: float
    threshold: float
    is_anomaly: bool
    inference_time_ms: float
    model_version: str
    created_at: datetime
