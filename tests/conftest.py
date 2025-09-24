from unittest.mock import MagicMock

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

from order_service.database import get_db
from order_service.main import app

load_dotenv(dotenv_path=".env.test")


@pytest.fixture(scope="session", autouse=True)
def override_get_db():
    def _get_db_override():
        yield MagicMock()

    app.dependency_overrides[get_db] = _get_db_override
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)
