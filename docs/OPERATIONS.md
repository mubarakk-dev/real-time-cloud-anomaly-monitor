# Operations

## Health model

- `/health` reports that the API process is running.
- `/ready` verifies Redis and PostgreSQL connectivity.
- Docker health checks supervise the API, Redis, PostgreSQL, and dashboard.
- `/metrics/` exposes request-independent application counters and inference latency.

## Recovery

Redis persistence uses append-only files. PostgreSQL and Redis use named Docker volumes. Stream messages are acknowledged after successful processing; failed messages remain in the consumer pending list and can be inspected with `XPENDING telemetry:events anomaly-workers`.

## Configuration

Runtime values are provided through environment variables. Commit `.env.example`, never `.env`. Use an external secret manager for non-local deployments.

## Useful commands

```bash
docker compose logs -f api worker
docker compose exec redis redis-cli XINFO GROUPS telemetry:events
docker compose exec postgres psql -U anomaly -d anomaly_monitor
docker compose restart worker
```

Persistent development data can be deliberately removed with `docker compose down -v`. This is destructive and should not be used where the volumes contain required history.
