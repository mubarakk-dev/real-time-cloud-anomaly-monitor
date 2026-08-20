from prometheus_client import Counter, Gauge, Histogram

EVENTS_ACCEPTED = Counter("telemetry_events_accepted_total", "Accepted telemetry observations", ("service",))
EVENTS_PROCESSED = Counter("telemetry_events_processed_total", "Processed telemetry observations", ("service",))
PREDICTIONS = Counter("window_predictions_total", "Completed window predictions", ("service", "outcome"))
INFERENCE_TIME = Histogram("model_inference_seconds", "Model inference duration")
ACTIVE_WINDOWS = Gauge("active_service_windows", "Number of service windows buffered in Redis")
WORKER_ERRORS = Counter("worker_errors_total", "Worker processing errors", ("exception",))
