# tests/test_cart_and_orders.py
import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from orders.models import Order  # adjust app name if not "shop"


class CartTests(APITestCase):
    def test_add_item_creates_cart_and_item(self) -> None:
        url = reverse("cart-items")
        payload = {
            "user_id": str(uuid.uuid4()),
            "product_id": str(uuid.uuid4()),
            "quantity": 2,
            "price": "50.00",
        }
        response = self.client.post(url, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert "cartId" in response.data
        assert response.data["totalAmount"] == "100.00"
        assert len(response.data["items"]) == 1


class OrderTests(APITestCase):
    @patch(
        "orders.services.external_apis.reserve_inventory",
        return_value={"reservationId": "RES123"},
    )
    @patch(
        "orders.services.external_apis.authorize_payment",
        return_value={"success": True, "transaction_id": "TX123"},
    )
    def test_create_order_success(
        self,
        mock_payment: MagicMock,
        mock_inventory: MagicMock,
    ) -> None:
        url = reverse("order-list")
        payload = {
            "user_id": str(uuid.uuid4()),
            "items": [
                {
                    "product_id": str(uuid.uuid4()),
                    "quantity": 1,
                    "price": "20.00",
                    "subtotal": "20.00",
                },
                {
                    "product_id": str(uuid.uuid4()),
                    "quantity": 2,
                    "price": "15.00",
                    "subtotal": "30.00",
                },
            ],
            "address_id": "ADDR123",
            "payment_method_id": "PM123",
            "currency": "USD",
        }
        response = self.client.post(url, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert Order.objects.count() == 1
        order = Order.objects.first()
        assert order.total_amount == Decimal("50.00")

    def test_update_order_status_illegal_transition(self) -> None:
        order = Order.objects.create(user_id=uuid.uuid4(), total_amount=Decimal("10.00"))
        url = reverse("order-status", args=[order.id])
        response = self.client.put(url, {"new_status": "DELIVERED"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Illegal transition" in response.data["detail"]

    def test_order_tracking(self) -> None:
        order = Order.objects.create(user_id=uuid.uuid4(), total_amount=Decimal("10.00"))
        url = reverse("order-tracking", args=[order.id])
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["orderId"] == str(order.id)
        assert response.data["currentStatus"] == order.status
        assert "trackingEvents" in response.data
