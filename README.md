# k8s-lab-status

A FastAPI status page for a Kubernetes lab environment. Periodically checks a configurable list of URLs and exposes their health over HTTP — with Prometheus metrics, a CSI secret demo endpoint, and load-testing knobs built in.

## Endpoints

| Route | Description |
|---|---|
| `GET /` | HTML status page |
| `GET /status` | JSON check results |
| `GET /health` | Liveness probe |
| `GET /ready` | Readiness probe (503 until first check completes) |
| `GET /metrics` | Prometheus-compatible metrics |
| `GET /secret-demo` | Reads a CSI-mounted secret and returns a masked preview |
| `GET /docs` | OpenAPI docs |

## Configuration

All configuration is via environment variables.

| Variable | Default | Description |
|---|---|---|
| `MONITOR_URLS` | `""` | Comma-separated list of URLs to check |
| `CHECK_INTERVAL` | `30` | Seconds between checks |
| `RESULTS_PATH` | `/mnt/efs/status.json` | Path to write JSON results (EFS ReadWriteMany demo) |
| `SECRET_PATH` | `/mnt/secrets/api-key` | Path to CSI-mounted secret file (Scenario 7) |
| `SIMULATE_LATENCY_MS` | `0` | Adds artificial latency to every response (Scenario 12) |
| `SIMULATE_ERROR_RATE` | `0.0` | Fraction of requests that return 500, e.g. `0.1` = 10% (Scenario 12) |

## Running locally

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv run uvicorn k8s_lab_status.main:app --reload
```

With URLs to monitor:

```bash
MONITOR_URLS="https://example.com,https://httpbin.org/get" uv run uvicorn k8s_lab_status.main:app --reload
```

## Running with Docker

```bash
docker build -t k8s-lab-status .
docker run -p 8000:8000 \
  -e MONITOR_URLS="https://example.com" \
  k8s-lab-status
```

## Lab scenarios

### Scenario 7 — Secrets Manager CSI Driver

Mount a secret as a file and point `SECRET_PATH` at it. The `/secret-demo` endpoint reads the file and returns the first four characters followed by `****`.

```yaml
# Example pod volume mount
volumeMounts:
  - name: secrets
    mountPath: /mnt/secrets
    readOnly: true
```

### Scenario 12 — Load testing

Use `SIMULATE_LATENCY_MS` and `SIMULATE_ERROR_RATE` to shape response behaviour without changing application code — useful for tuning k6/Locust scenarios.

```bash
# 200ms latency, 5% error rate
SIMULATE_LATENCY_MS=200 SIMULATE_ERROR_RATE=0.05 uv run uvicorn k8s_lab_status.main:app
```

### Scenario 13 — Observability

`/health` and `/ready` serve as liveness and readiness probes. `/metrics` returns Prometheus text format and exposes:

- `http_requests_total` — request count by method, path, and status code
- `http_request_duration_seconds` — request latency histogram
- `monitored_endpoint_up` — 1/0 gauge per monitored URL
- `monitored_endpoint_latency_ms` — last recorded latency per monitored URL

### Core — EFS ReadWriteMany

On each check cycle the app writes a JSON snapshot to `RESULTS_PATH`. In a K8s lab this can be an EFS volume mounted `ReadWriteMany` across multiple pods, demonstrating shared persistent storage.

## Development

```bash
# Lint
uv run ruff check .
uv run ruff format --check .

# Test
uv run pytest -v
```

## CI/CD

GitHub Actions pipeline on every push:

1. **Lint** — ruff check + format
2. **Test** — pytest
3. **Build / Scan / Push** — Docker build, Grype vulnerability scan, push to Docker Hub on merge to `main`

Requires `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` repository secrets.
