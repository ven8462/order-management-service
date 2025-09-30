from fastapi.testclient import TestClient


def test_health_check_succeeds(client: TestClient) -> None:
    response = client.get("/health/ping")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}
