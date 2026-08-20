# Security

The ingestion endpoint requires an `X-API-Key` value compared with the configured secret using constant-time comparison. Environment files, key files, credential JSON, and common secret filenames are excluded from Git and Docker build contexts.

The local stack intentionally exposes services on loopback ports for demonstration. Before internet-facing deployment:

- terminate TLS at a trusted reverse proxy or load balancer;
- replace the shared API key with managed workload identity or short-lived credentials;
- restrict PostgreSQL and Redis to private networks;
- store secrets in a managed secret service;
- add rate limits and request-size limits;
- define retention and deletion controls for telemetry;
- run dependency and container-image scanning;
- forward structured logs without recording credentials.

No real customer or production telemetry is included in this repository.
