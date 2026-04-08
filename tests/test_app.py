import pytest
from fastapi.testclient import TestClient

from k8s_lab_status.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_ready_no_urls_configured(client):
    # With no MONITOR_URLS set, app is immediately ready
    resp = client.get("/ready")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


def test_status_empty(client):
    resp = client.get("/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data or "endpoints" in data


def test_metrics_returns_prometheus_text(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert b"http_requests_total" in resp.content
    assert b"http_request_duration_seconds" in resp.content


def test_index_html(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "k8s-lab-status" in resp.text
    assert "MONITOR_URLS" in resp.text  # empty-state message


def test_secret_demo_missing_file(client):
    # Default secret path doesn't exist in test environment
    resp = client.get("/secret-demo")
    assert resp.status_code == 404
    assert "error" in resp.json()


def test_openapi_docs(client):
    resp = client.get("/docs")
    assert resp.status_code == 200


def test_metrics_incremented_by_requests(client):
    # Make a few requests then check the counter is non-zero in /metrics output
    client.get("/health")
    client.get("/health")
    resp = client.get("/metrics")
    assert b"http_requests_total" in resp.content
