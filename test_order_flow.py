import os
import django
import time
import uuid
from decimal import Decimal

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.test import Client
from orders.models import Order, OrderTracking

# ------------------ Test payload ------------------
payload = {
    "user_id": str(uuid.uuid4()),
    "items": [
        {
            "product_id": str(uuid.uuid4()),
            "quantity": 2,
            "price": 50,
            "subtotal": 100
        },
        {
            "product_id": str(uuid.uuid4()),
            "quantity": 1,
            "price": 30,
            "subtotal": 30
        }
    ],
    "address_id": str(uuid.uuid4()),
    "payment_method_id": str(uuid.uuid4())
}

# ------------------ Send POST request ------------------
client = Client()
response = client.post("/api/orders/", data=payload, content_type="application/json")
print("Order creation response status:", response.status_code)
print("Response data:", response.json())

# ------------------ Wait for consumer to process event ------------------
print("Waiting 5 seconds for Kafka consumer to process event...")
time.sleep(5)  # adjust if needed

# ------------------ Check orders in DB ------------------
order = Order.objects.filter(user_id=payload["user_id"]).first()
if order:
    print(f"Order ID: {order.id}, Status: {order.status}")
    tracking_events = OrderTracking.objects.filter(order=order)
    for t in tracking_events:
        print(f"Tracking: {t.status} at {t.location}")
else:
    print("Order not found in database.")
