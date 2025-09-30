import json
import logging
import threading

from confluent_kafka import Consumer
from prometheus_client import Counter
from sqlalchemy.orm.session import Session as SessionType

from order_service.config import get_settings

from . import crud
from .database import SessionLocal
from .models import OrderStatusEnum
from .producer import publish_event

settings = get_settings()

EVENTS_CONSUMED_TOTAL = Counter(
    "order_service_events_consumed_total",
    "Total number of events successfully consumed and processed",
    ["topic"],
)
EVENTS_PROCESSING_FAILURES_TOTAL = Counter(
    "order_service_event_processing_failures_total",
    "Total number of non-fatal errors during event processing (retries)",
    ["topic"],
)
EVENTS_SENT_TO_DLQ_TOTAL = Counter(
    "order_service_events_sent_to_dlq_total",
    "Total number of events sent to the Dead-Letter Queue",
    ["topic"],
)

logger = logging.getLogger(__name__)


def process_payment_successful(db: SessionType, event_data: dict) -> None:
    order_id = event_data["orderId"]
    crud.update_order_status(db, order_id, OrderStatusEnum.INVENTORY_RESERVING)
    publish_event("reserve_inventory_request", {"orderId": order_id, "items": event_data["items"]})


def process_inventory_reserved(db: SessionType, event_data: dict) -> None:
    order_id = event_data["orderId"]
    crud.update_order_status(db, order_id, OrderStatusEnum.CONFIRMED)
    publish_event("order_confirmed", {"orderId": order_id})


def process_payment_failed(db: SessionType, event_data: dict) -> None:
    order_id = event_data["orderId"]
    crud.update_order_status(db, order_id, OrderStatusEnum.FAILED)


def process_inventory_reservation_failed(db: SessionType, event_data: dict) -> None:
    order_id = event_data["orderId"]
    crud.update_order_status(db, order_id, OrderStatusEnum.FAILED)
    publish_event("refund_payment_request", {"orderId": order_id})


TOPIC_HANDLERS = {
    "payment_successful": process_payment_successful,
    "inventory_reserved": process_inventory_reserved,
    "payment_failed": process_payment_failed,
    "inventory_reservation_failed": process_inventory_reservation_failed,
}


def consume_events() -> None:
    conf = {
        "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
        "group.id": "order_service_group",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    }
    consumer = Consumer(conf)
    consumer.subscribe(list(TOPIC_HANDLERS.keys()))
    logger.info("Kafka consumer subscribed to topics: %s", list(TOPIC_HANDLERS.keys()))

    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                logger.error("Kafka consumer error: %s", msg.error())
                continue

            topic = msg.topic()
            try:
                event_data = json.loads(msg.value().decode("utf-8"))
                logger.info("Consumed event from topic '%s'", topic)

                handler = TOPIC_HANDLERS.get(topic)
                if handler:
                    db = SessionLocal()
                    try:
                        handler(db, event_data)
                        consumer.commit(asynchronous=False)
                        EVENTS_CONSUMED_TOTAL.labels(topic=topic).inc()
                    finally:
                        db.close()
                else:
                    logger.warning("No handler found for topic: %s. Discarding message.", topic)
                    consumer.commit(asynchronous=False)

            except Exception as e:
                logger.exception(
                    "FATAL: Unhandled exception processing event from topic '%s': %s",
                    topic,
                    e,
                )
                EVENTS_PROCESSING_FAILURES_TOTAL.labels(topic=topic).inc()

                dlq_topic = f"{topic}_dlq"
                logger.info("Sending poisonous message to DLQ topic: %s", dlq_topic)
                try:
                    publish_event(
                        dlq_topic,
                        {"original_message": msg.value().decode("utf-8"), "error": str(e)},
                    )
                    EVENTS_SENT_TO_DLQ_TOTAL.labels(topic=dlq_topic).inc()
                    consumer.commit(asynchronous=False)
                except (ConnectionError, TimeoutError, ValueError) as dlq_e:
                    logger.critical(
                        "CRITICAL FAILURE: Could not send message to DLQ. Error: %s",
                        dlq_e,
                        exc_info=True,
                    )

    finally:
        consumer.close()
        logger.info("Kafka consumer has shut down.")


def start_consumer_thread() -> None:
    consumer_thread = threading.Thread(target=consume_events, daemon=True)
    consumer_thread.start()
