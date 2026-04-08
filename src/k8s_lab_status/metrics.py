from prometheus_client import Counter, Gauge, Histogram

# Scenario 13: Prometheus-compatible metrics

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests by method, path, and status code",
    ["method", "path", "status"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
)

ENDPOINT_UP = Gauge(
    "monitored_endpoint_up",
    "Whether a monitored endpoint is reachable (1=up, 0=down)",
    ["url"],
)

ENDPOINT_LATENCY = Gauge(
    "monitored_endpoint_latency_ms",
    "Last recorded latency for a monitored endpoint in milliseconds",
    ["url"],
)
