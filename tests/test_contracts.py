from pathlib import Path

from app.model import ModelRuntime
from app.schemas import TelemetryEvent


def test_public_event_contract_excludes_ground_truth():
    fields = set(TelemetryEvent.model_fields)
    assert {"label", "incident_id", "anomaly_type", "anomaly_label"}.isdisjoint(fields)


def test_persisted_model_loads_with_version_and_valid_threshold():
    runtime = ModelRuntime(str(Path("models/window_random_forest.joblib")))
    assert runtime.window_seconds == 30
    assert 0 <= runtime.threshold <= 1
    assert len(runtime.version) == 12


def test_model_scores_valid_behavioural_features():
    runtime = ModelRuntime(str(Path("models/window_random_forest.joblib")))
    score, decision, elapsed_ms = runtime.predict(
        {
            "service": "payment-service",
            "avg_response_time": 850.0,
            "max_response_time": 1200.0,
            "avg_cpu_usage": 88.0,
            "max_cpu_usage": 98.0,
            "avg_memory_usage": 84.0,
            "max_memory_usage": 95.0,
            "error_rate": 0.35,
            "warn_rate": 0.40,
            "error_log_rate": 0.20,
            "log_count": 30,
        }
    )
    assert 0 <= score <= 1
    assert decision == (score >= runtime.threshold)
    assert elapsed_ms >= 0
