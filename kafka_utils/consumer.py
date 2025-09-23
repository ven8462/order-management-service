import os
import django
import json
from kafka import KafkaConsumer

# Make sure Django knows where to find settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()


from orders.tasks import (
    handle_payment_successful,
    handle_payment_failed,
    handle_inventory_reserved,
    handle_inventory_failed,
    handle_inventory_timeout,
)

def start_consumer():
    consumer = KafkaConsumer(
        "order-events",
        bootstrap_servers=["localhost:9092"],
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="order-service",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    )

    print("Kafka consumer started. Listening for events...")

    for message in consumer:
        event = message.value
        print(f"Received event: {event}")

        process_event(event)


def process_event(event: dict):
    event_type = event.get("type")

    if event_type == "PaymentSuccessful":
        handle_payment_successful.delay(event)
    elif event_type == "PaymentFailed":
        handle_payment_failed.delay(event)
    elif event_type == "InventoryReserved":
        handle_inventory_reserved.delay(event)
    elif event_type == "InventoryFailed":
        handle_inventory_failed.delay(event)
    elif event_type == "InventoryTimeout":
        handle_inventory_timeout.delay(event)
    else:
        print(f"Unknown event type: {event_type}")