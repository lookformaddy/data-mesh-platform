"""API tests. They auto-skip when FastAPI/httpx are not installed."""

import pytest

fastapi = pytest.importorskip("fastapi", reason="FastAPI not installed")
pytest.importorskip("httpx", reason="httpx not installed")

from fastapi.testclient import TestClient  # noqa: E402

from datamesh.models import HealthSignal  # noqa: E402
from datamesh.service import create_app  # noqa: E402


@pytest.fixture
def client(mesh, good_signal):
    mesh.record_signal(good_signal)
    return TestClient(create_app(mesh))


def test_health_endpoint(client):
    assert client.get("/health").json() == {"status": "ok"}
    resp = client.get("/products/orders.daily/health")
    assert resp.status_code == 200 and resp.json()["grade"] == "healthy"


def test_products_and_impact_endpoints(client):
    assert client.get("/products?query=orders").json()[0]["product_id"] == "orders.daily"
    impact = client.get("/products/inventory.stock/impact").json()
    assert impact["downstream"] == {"orders.daily": 1}
    assert client.get("/products/nope").status_code == 404
    gov = client.get("/products/orders.daily/governance").json()
    assert gov["allowed"] is True
