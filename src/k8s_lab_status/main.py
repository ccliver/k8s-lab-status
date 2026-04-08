import asyncio
import random
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from .checker import run_checker
from .config import Settings
from .metrics import ENDPOINT_LATENCY, ENDPOINT_UP, REQUEST_COUNT, REQUEST_LATENCY

settings = Settings()
_results: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_event = asyncio.Event()
    task = asyncio.create_task(run_checker(settings, _results, stop_event))
    yield
    stop_event.set()
    await task


app = FastAPI(title=settings.app_name, lifespan=lifespan)


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    # Scenario 12: inject artificial latency for load-testing experiments
    if settings.simulate_latency_ms > 0:
        await asyncio.sleep(settings.simulate_latency_ms / 1000)

    # Scenario 12: inject random errors to test resilience
    if (
        settings.simulate_error_rate > 0
        and random.random() < settings.simulate_error_rate
    ):
        REQUEST_COUNT.labels(
            method=request.method, path=request.url.path, status="500"
        ).inc()
        return JSONResponse({"error": "simulated error"}, status_code=500)

    start = time.monotonic()
    response = await call_next(request)
    duration = time.monotonic() - start

    # Scenario 13: record metrics
    REQUEST_COUNT.labels(
        method=request.method,
        path=request.url.path,
        status=str(response.status_code),
    ).inc()
    REQUEST_LATENCY.labels(method=request.method, path=request.url.path).observe(
        duration
    )

    return response


# ---------------------------------------------------------------------------
# Scenario 13: Health / readiness probes
# ---------------------------------------------------------------------------


@app.get("/health", tags=["observability"])
async def health():
    """Liveness probe."""
    return {"status": "ok"}


@app.get("/ready", tags=["observability"])
async def ready():
    """Readiness probe — not ready until first check completes."""
    urls = settings.get_urls()
    if not urls or _results:
        return {"status": "ready"}
    return JSONResponse({"status": "not ready"}, status_code=503)


# Scenario 13: Prometheus metrics endpoint
@app.get("/metrics", tags=["observability"])
async def metrics():
    """Prometheus-compatible metrics."""
    for url, data in _results.get("endpoints", {}).items():
        ENDPOINT_UP.labels(url=url).set(1 if data.get("up") else 0)
        if data.get("latency_ms") is not None:
            ENDPOINT_LATENCY.labels(url=url).set(data["latency_ms"])
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ---------------------------------------------------------------------------
# Core: status API
# ---------------------------------------------------------------------------


@app.get("/status", tags=["status"])
async def status():
    """JSON status of all monitored endpoints."""
    return _results or {"message": "No checks run yet — set MONITOR_URLS env var."}


# ---------------------------------------------------------------------------
# Scenario 7: Secrets Manager CSI Driver demo
# ---------------------------------------------------------------------------


@app.get("/secret-demo", tags=["scenarios"])
async def secret_demo():
    """Read a secret from a CSI-mounted volume path (Scenario 7)."""
    try:
        value = Path(settings.secret_path).read_text().strip()
        preview = (value[:4] + "****") if len(value) > 4 else "****"
        return {"secret_path": settings.secret_path, "value_preview": preview}
    except FileNotFoundError:
        return JSONResponse(
            {"error": f"Secret not found at {settings.secret_path}"},
            status_code=404,
        )
    except OSError as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


# ---------------------------------------------------------------------------
# Root: HTML status page
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse, tags=["status"])
async def index():
    endpoints = _results.get("endpoints", {})
    checked_at = _results.get("checked_at")
    ts = f"{checked_at:.0f}" if checked_at else "never"

    rows = ""
    for url, data in endpoints.items():
        icon = "&#x2705;" if data.get("up") else "&#x274C;"
        code = data.get("status_code") or "—"
        latency = f"{data.get('latency_ms', '—')} ms"
        error = data.get("error", "")
        rows += (
            f"<tr><td>{icon}</td>"
            f'<td><a href="{url}">{url}</a></td>'
            f"<td>{code}</td><td>{latency}</td><td>{error}</td></tr>"
        )

    if not rows:
        rows = (
            "<tr><td colspan=5>No URLs configured"
            " — set <code>MONITOR_URLS</code> env var.</td></tr>"
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{settings.app_name}</title>
  <style>
    body {{ font-family: monospace; padding: 2rem; max-width: 900px; margin: auto; }}
    h1 {{ border-bottom: 2px solid #333; padding-bottom: .5rem; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
    th, td {{ border: 1px solid #ccc; padding: .5rem 1rem; text-align: left; }}
    th {{ background: #f5f5f5; }}
    nav {{ margin-top: 1.5rem; }}
    nav a {{ margin-right: 1rem; }}
  </style>
</head>
<body>
  <h1>{settings.app_name}</h1>
  <p>Last checked: <time>{ts}</time> &mdash; interval: {settings.check_interval}s</p>
  <table>
    <thead><tr><th>Status</th><th>URL</th><th>HTTP</th><th>Latency</th><th>Error</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <nav>
    <a href="/status">/status</a>
    <a href="/metrics">/metrics</a>
    <a href="/health">/health</a>
    <a href="/ready">/ready</a>
    <a href="/secret-demo">/secret-demo</a>
    <a href="/docs">/docs</a>
  </nav>
</body>
</html>"""


def main() -> None:
    import uvicorn

    uvicorn.run("k8s_lab_status.main:app", host="0.0.0.0", port=8000, reload=False)
