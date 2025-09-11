# tests/test_cart_and_orders.py
import uuid
from decimal import Decimal
from unittest.mock import patch
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from orders.models import Cart, Order  # adjust app name if not "shop"


class CartTests(APITestCase):
    def test_add_item_creates_cart_and_item(self):
        url = reverse("cart-items")
        payload = {
            "user_id": str(uuid.uuid4()),
            "product_id": str(uuid.uuid4()),
            "quantity": 2,
            "price": "50.00",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("cartId", response.data)
        self.assertEqual(response.data["totalAmount"], "100.00")
        self.assertEqual(len(response.data["items"]), 1)


class OrderTests(APITestCase):
    @patch("orders.views.services.reserve_inventory", return_value=True)
    @patch("orders.views.services.authorize_payment", return_value={"success": True, "transaction_id": "TX123"})
    def test_create_order_success(self, mock_payment, mock_inventory):
        url = reverse("order-list")
        payload = {
            "user_id": str(uuid.uuid4()),
            "items": [
               {"product_id": str(uuid.uuid4()), "quantity": 1, "price": "20.00", "subtotal": "20.00"},
               {"product_id": str(uuid.uuid4()), "quantity": 2, "price": "15.00", "subtotal": "30.00"},
            ],
            "address_id": "ADDR123",
            "payment_method_id": "PM123",
            "currency": "USD",
        }
        response = self.client.post(url, payload, format="json")
        #print(response.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.first()
        self.assertEqual(order.total_amount, Decimal("50.00"))

    def test_update_order_status_illegal_transition(self):
        order = Order.objects.create(user_id=uuid.uuid4(), total_amount=Decimal("10.00"))
        url = reverse("order-status", args=[order.id])
        response = self.client.put(url, {"new_status": "DELIVERED"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Illegal transition", response.data["detail"])

    def test_order_tracking(self):
        order = Order.objects.create(user_id=uuid.uuid4(), total_amount=Decimal("10.00"))
        url = reverse("order-tracking", args=[order.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["orderId"], str(order.id))
        self.assertEqual(response.data["currentStatus"], order.status)
        self.assertIn("trackingEvents", response.data)



