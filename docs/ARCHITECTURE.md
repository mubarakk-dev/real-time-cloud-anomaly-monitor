# Architecture

## Data path

The ingestion API validates raw telemetry and appends accepted events to a Redis Stream. It returns `202 Accepted` with the stream event ID, avoiding synchronous model work on the request path.

A separate consumer-group worker reads events, advances an event-time watermark, and maintains one Redis hash for each service/window pair. Completed hashes are converted into the model feature contract. A short Redis lock makes window finalisation exclusive if more than one consumer is running.

The persisted scikit-learn pipeline performs categorical preprocessing and prediction. The worker applies the threshold stored with the artifact, inserts the decision into PostgreSQL, publishes it over Redis Pub/Sub, and records Prometheus counters and latency histograms.

The API reads prediction history from PostgreSQL and relays Pub/Sub messages over WebSocket. The dashboard uses the REST history endpoints so a browser refresh does not lose previous alerts.

## Delivery semantics

Redis Stream entries are acknowledged only after window processing succeeds. A failed event remains pending for recovery. Prediction persistence is at-least-once at the event-processing boundary; strict exactly-once delivery would require an idempotency key and database uniqueness constraint spanning the stream event and completed window.

## Scaling boundary

The API is stateless and can be replicated. Worker replication is supported by the Redis consumer group and window lock, although throughput and contention must be measured before increasing replicas. PostgreSQL and Redis are single instances in the local Compose topology; managed or clustered services are appropriate for resilient deployments.
