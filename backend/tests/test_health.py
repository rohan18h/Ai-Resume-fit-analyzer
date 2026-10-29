"""Step 0 tests: health endpoint, error format, CORS."""

from fastapi.testclient import TestClient

from app.main import app


def test_health_ok() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "model_loaded": False, "version": "1.0.0"}


def test_unknown_route_uses_error_format() -> None:
    with TestClient(app) as client:
        response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_cors_allows_frontend_origin() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_blocks_other_origin() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in response.headers
