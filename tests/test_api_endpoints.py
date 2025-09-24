from unittest.mock import patch


def test_health_check_succeeds(client) -> None:
    with patch("sqlalchemy.orm.Session.execute"):
        response = client.get("/health/ping")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "database": "connected"}
