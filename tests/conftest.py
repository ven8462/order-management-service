import os
from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from order_service.database import get_db
from order_service.main import app
from order_service.user_management_client import get_current_user



@pytest.fixture(scope="session", autouse=True)
def test_env_vars():
    os.environ.setdefault("POSTGRES_USER", "test")
    os.environ.setdefault("POSTGRES_PASSWORD", "test")
    os.environ.setdefault("POSTGRES_DB", "test_db")
    os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
    os.environ.setdefault("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    os.environ.setdefault("REDIS_HOST", "localhost")
    os.environ.setdefault("REDIS_PORT", "6379")
    os.environ.setdefault("INVENTORY_SERVICE_URL", "http://fake-inventory")
    os.environ.setdefault("SECRET_KEY", "testsecret")
    os.environ.setdefault("PAYMENT_SERVICE_BASE_URL", "http://fake-payment")


@pytest.fixture(scope="session", autouse=True)
def override_get_db() -> Iterator[None]:
    def _get_db_override() -> Iterator[None]:
        yield MagicMock()

    app.dependency_overrides[get_db] = _get_db_override
    yield
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def override_current_user():
    def _fake_user():
        return {"user_id": "test-user"}

    app.dependency_overrides[get_current_user] = _fake_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
