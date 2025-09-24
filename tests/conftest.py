from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from order_service.database import get_db
from order_service.main import app


@pytest.fixture(scope="session", autouse=True)
def override_get_db() -> Iterator[None]:
    def _get_db_override() -> Iterator[None]:
        yield MagicMock()

    app.dependency_overrides[get_db] = _get_db_override
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
