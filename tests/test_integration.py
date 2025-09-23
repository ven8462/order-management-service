import pytest
import time
from kafka import KafkaProducer, KafkaConsumer
from orders.models import Order, OrderTracking
from orders.tasks import handle_payment_successful
from django.conf import settings

KAFKA_BOOTSTRAP = "localhost:9093"
KAFKA_TOPIC = "payments"

@pytest.mark.django_db(transaction=True)
def test_payment_successful_integration():
    # 1️⃣ Create a pending order
    order = Order.objects.create(status=Order.Status.PENDING)

    # 2️⃣ Publish an event to Kafka
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda m: json.dumps(m).encode("utf-8")
    )
    event = {"type": "PaymentSuccessful", "order_id": order.id, "items": ["item1"]}
    producer.send(KAFKA_TOPIC, event)
    producer.flush()

    # 3️⃣ Start a consumer manually (simulate Django management command)
    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        auto_offset_reset="earliest",
        group_id="test-group",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    )

    # 4️⃣ Consume the event and trigger the task
    for message in consumer:
        msg = message.value
        if msg["type"] == "PaymentSuccessful":
            handle_payment_successful(msg)
        break  # only test one message

    order.refresh_from_db()
    assert order.status == Order.Status.PAID
    tracking = OrderTracking.objects.get(order=order)
    assert tracking.location == "Payment Successful"