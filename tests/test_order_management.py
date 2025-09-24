import pytest
from unittest.mock import patch
from starlette.testclient import TestClient

from src.main import app as main_app


@pytest.fixture
def client():
    return TestClient(main_app)


# The patches must point to where the functions are USED, not where they are defined.
# They are used in src.main, so the path should be src.main.function_name
@patch("src.main.call_inventory_service")
@patch("src.main.call_payment_service")
@patch("src.main.save_order_to_db")
def test_create_order_success(mock_save_to_db, mock_payment, mock_inventory, client):
    """Verifies the core critical path: Inventory -> Payment -> Order Confirmed."""
    # Arrange
    mock_inventory.return_value = {"status": "reserved"}
    mock_payment.return_value = {"transaction_id": "tx123", "status": "approved"}

    order_data = {
        "user_id": "user-abc",
        "items": [{"product_id": "prod-1", "quantity": 2, "price": 50.00}],
        "address_id": "addr-99",
        "payment_method_id": "pm-789",
    }

    # Act
    response = client.post("/orders", json=order_data)

    # Assert
    assert response.status_code == 201
    assert response.json()["status"] == "CONFIRMED"
    mock_inventory.assert_called_once()
    mock_payment.assert_called_once()
    mock_save_to_db.assert_called_once()


@patch("src.main.call_inventory_service")
@patch("src.main.call_payment_service")
@patch("src.main.save_order_to_db")
def test_create_order_inventory_failure(mock_save_to_db, mock_payment, mock_inventory, client):
    """Verifies that an order fails if stock cannot be reserved."""
    # Arrange
    mock_inventory.side_effect = Exception("Stock unavailable")
    order_data = {
        "user_id": "user-abc",
        "items": [{"product_id": "prod-1", "quantity": 2, "price": 50.00}],
        "address_id": "addr-99",
        "payment_method_id": "pm-789",
    }

    # Act
    response = client.post("/orders", json=order_data)

    # Assert
    assert response.status_code == 400
    assert response.json()["detail"] == "Failed to reserve stock."
    mock_inventory.assert_called_once()
    mock_payment.assert_not_called()
    mock_save_to_db.assert_not_called()


@patch("src.main.call_inventory_service")
@patch("src.main.call_payment_service")
@patch("src.main.save_order_to_db")
def test_create_order_payment_breaker_tripped(
    mock_save_to_db, mock_payment, mock_inventory, client
):
    """Tests the resilience pattern: handling a broken dependency."""
    # Arrange
    mock_inventory.return_value = {"status": "reserved"}
    mock_payment.side_effect = Exception("Payment service is down")
    order_data = {
        "user_id": "user-abc",
        "items": [{"product_id": "prod-1", "quantity": 2, "price": 50.00}],
        "address_id": "addr-99",
        "payment_method_id": "pm-789",
    }

    # Act
    response = client.post("/orders", json=order_data)

    # Assert
    assert response.status_code == 500
    assert "Payment service is down" in response.json()["detail"]
    mock_inventory.assert_called_once()
    mock_payment.assert_called_once()
    mock_save_to_db.assert_not_called()


@patch("src.main.get_order_details")
def test_get_order_details_found(mock_db_call, client):
    """Retrieves order details successfully."""
    # Arrange
    mock_db_call.return_value = {"orderId": "abc123", "status": "SHIPPED", "totalAmount": 120.00}

    # Act
    response = client.get("/orders/abc123")

    # Assert
    assert response.status_code == 200
    assert response.json()["orderId"] == "abc123"
    mock_db_call.assert_called_once_with("abc123")


@patch("src.main.get_order_details")
def test_get_order_details_not_found(mock_db_call, client):
    """Handles an invalid or non-existent order ID gracefully."""
    # Arrange
    mock_db_call.return_value = None  # Database returns nothing

    # Act
    response = client.get("/orders/non-existent-id")

    # Assert
    assert response.status_code == 404
    assert "Order not found" in response.json()["detail"]
    mock_db_call.assert_called_once_with("non-existent-id")
