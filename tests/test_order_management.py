from types import SimpleNamespace
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from order_service.main import app as main_app
from order_service.models import OrderStatusEnum


@pytest.fixture
def client():
    return TestClient(main_app)


def test_create_order_success(client):
    order_payload = {
        "order_create": {
            "items": [
                {"product_id": "p1", "quantity": 2, "price": 1000.0},
                {"product_id": "p2", "quantity": 1, "price": 1500.0},
            ],
            "shipping_address": "Nairobi, Kenya",
        },
    }

    with (
        patch("order_service.api.inventory_client.reserve_stock") as mock_reserve,
        patch("order_service.api.create_payment") as mock_payment,
        patch("order_service.api.crud.create_order") as mock_create_order,
        patch("order_service.api.crud.update_order_status") as mock_update_order,
    ):
        mock_reserve.return_value = True

        fake_db_order = SimpleNamespace(
            id=123,
            total_amount=3500.0,
            status=OrderStatusEnum.PENDING,
            items=[],
        )
        mock_create_order.return_value = fake_db_order
        mock_payment.return_value = {"status": "SUCCEEDED"}

        def _update(db, order_id, status):
            fake_db_order.status = status
            return fake_db_order

        mock_update_order.side_effect = _update

        response = client.post("/orders/", json=order_payload)

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == 123
        assert data["status"] == OrderStatusEnum.CONFIRMED


def test_create_order_payment_failed(client):
    order_payload = {
        "order_create": {
            "items": [{"product_id": "p1", "quantity": 1, "price": 1500.0}],
            "shipping_address": "Nairobi",
        },
    }

    with (
        patch("order_service.api.inventory_client.reserve_stock") as mock_reserve,
        patch("order_service.api.create_payment") as mock_payment,
        patch("order_service.api.crud.create_order") as mock_create_order,
        patch("order_service.api.crud.update_order_status") as mock_update_order,
    ):
        mock_reserve.return_value = True

        fake_db_order = SimpleNamespace(
            id=124,
            total_amount=1500.0,
            status=OrderStatusEnum.PENDING,
            items=[SimpleNamespace(id=1, product_id="p1", quantity=1, price=1500.0)],
        )
        mock_create_order.return_value = fake_db_order
        mock_payment.return_value = {"status": "FAILED"}

        def _update(db, order_id, status):
            fake_db_order.status = status
            return fake_db_order

        mock_update_order.side_effect = _update

        response = client.post("/orders/", json=order_payload)

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == OrderStatusEnum.FAILED
        assert data["id"] == 124
        assert len(data["items"]) == 1
