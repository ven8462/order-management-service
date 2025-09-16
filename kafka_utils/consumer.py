import json
import threading
import time
import signal
from kafka import KafkaConsumer
from orders.models import Order, OrderTracking
from kafka_utils.producer import publish_event

# Global stop flag for graceful shutdown
STOP = False

# ---------------------- Graceful Shutdown ----------------------
def signal_handler(sig, frame):
    global STOP
    print("Stopping Kafka consumer...")
    STOP = True

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ---------------------- Event Handlers ----------------------
def handle_payment_successful(event):
    order = Order.objects.filter(id=event["order_id"]).first()
    if not order:
        return
    order.status = Order.Status.CONFIRMED
    order.save(update_fields=["status", "updated_at"])
    OrderTracking.objects.create(order=order, status=order.status, location="Payment Successful")
    publish_event("reserve-inventory", {"order_id": order.id, "items": event.get("items", [])})

def handle_payment_failed(event):
    order = Order.objects.filter(id=event["order_id"]).first()
    if not order:
        return
    order.status = Order.Status.CANCELLED
    order.save(update_fields=["status", "updated_at"])
    OrderTracking.objects.create(order=order, status=order.status, location="Payment Failed")

def handle_inventory_reserved(event):
    order = Order.objects.filter(id=event["order_id"]).first()
    if not order:
        return
    order.status = Order.Status.COMPLETED
    order.save(update_fields=["status", "updated_at"])
    OrderTracking.objects.create(order=order, status=order.status, location="Inventory Reserved")

def handle_inventory_failed(event):
    order = Order.objects.filter(id=event["order_id"]).first()
    if not order:
        return
    order.status = Order.Status.CANCELLED
    order.save(update_fields=["status", "updated_at"])
    OrderTracking.objects.create(order=order, status=order.status, location="Inventory Failed")
    publish_event("cancel-payment", {"order_id": order.id})

def handle_inventory_timeout(event):
    order = Order.objects.filter(id=event["order_id"]).first()
    if not order:
        return
    order.status = Order.Status.CANCELLED
    order.save(update_fields=["status", "updated_at"])
    OrderTracking.objects.create(order=order, status=order.status, location="Inventory Timeout")
    publish_event("cancel-payment", {"order_id": order.id})

# Map Kafka topics to handlers
HANDLERS = {
    "payment-successful": handle_payment_successful,
    "payment-failed": handle_payment_failed,
    "inventory-reserved": handle_inventory_reserved,
    "inventory-failed": handle_inventory_failed,
    "inventory-timeout": handle_inventory_timeout,
}

# ---------------------- Consumer Loop ----------------------
def start_consumer():
    global STOP
    while not STOP:
        consumer = None
        try:
            consumer = KafkaConsumer(
                "payment-successful",
                "payment-failed",
                "inventory-reserved",
                "inventory-failed",
                "inventory-timeout",
                bootstrap_servers="localhost:9092",
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                group_id="order-service",
                auto_offset_reset="earliest",
            )
            print("Order Service Kafka Consumer started...")

            for message in consumer:
                if STOP:
                    break
                topic = message.topic
                event = message.value
                handler = HANDLERS.get(topic)
                if handler:
                    # Run each message handler in a separate daemon thread
                    threading.Thread(target=handler, args=(event,), daemon=True).start()

        except Exception as e:
            print(f"Kafka consumer error: {e}. Retrying in 5 seconds...")
            time.sleep(5)

        finally:
            if consumer:
                try:
                    consumer.close()
                except:
                    pass

    print("Kafka consumer stopped gracefully.")