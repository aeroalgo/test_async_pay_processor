import pytest

pytestmark = pytest.mark.integration


def test_health_ok(test_client):
    response = test_client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_protected_route_without_api_key_returns_401(test_client):
    response = test_client.get("/api/v1/health/protected")
    assert response.status_code == 401


def test_protected_route_with_invalid_api_key_returns_401(test_client):
    response = test_client.get(
        "/api/v1/health/protected",
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 401


def test_protected_route_with_valid_api_key_returns_200(test_client):
    response = test_client.get(
        "/api/v1/health/protected",
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 200
    assert response.json() == {"authenticated": True}
