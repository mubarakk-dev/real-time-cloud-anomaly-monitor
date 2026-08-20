CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    window_start TIMESTAMPTZ NOT NULL,
    window_end TIMESTAMPTZ NOT NULL,
    service VARCHAR(100) NOT NULL,
    anomaly_score DOUBLE PRECISION NOT NULL,
    threshold DOUBLE PRECISION NOT NULL,
    is_anomaly BOOLEAN NOT NULL,
    inference_time_ms DOUBLE PRECISION NOT NULL,
    model_version VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_predictions_window_end ON predictions (window_end DESC);
CREATE INDEX IF NOT EXISTS ix_predictions_service ON predictions (service);
CREATE INDEX IF NOT EXISTS ix_predictions_is_anomaly ON predictions (is_anomaly);
