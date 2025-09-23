# File: order_service/consumer.py
"""
This module contains the Kafka consumer and the core Saga logic.
It's designed for resilience with a Dead-Letter Queue (DLQ) for poison pill messages
and Prometheus metrics for monitoring.
"""

import json
import logging
import threading

from confluent_kafka import Consumer, KafkaException
from sqlalchemy.orm.session import Session as SessionType

from . import crud
from .config import settings
from .database import SessionLocal
from .models import OrderStatusEnum
# We use the same producer to send messages to the DLQ or for compensation events
from .producer import publish_event
from prometheus_client import Counter

# --- Prometheus Metrics ---
EVENTS_CONSUMED_TOTAL = Counter(
    "order_service_events_consumed_total",
    "Total number of events successfully consumed and processed",
    ["topic"]
)
EVENTS_PROCESSING_FAILURES_TOTAL = Counter(
    "order_service_event_processing_failures_total",
    "Total number of non-fatal errors during event processing (retries)",
    ["topic"]
)
EVENTS_SENT_TO_DLQ_TOTAL = Counter(
    "order_service_events_sent_to_dlq_total",
    "Total number of events sent to the Dead-Letter Queue",
    ["topic"]
)

logger = logging.getLogger(__name__)

# --- Saga Logic Handlers ---

def process_payment_successful(db: SessionType, event_data: dict):
    order_id = event_data["orderId"]
    crud.update_order_status(db, order_id, OrderStatusEnum.INVENTORY_RESERVING)
    # Next step in the saga: request inventory reservation
    publish_event("reserve_inventory_request", {"orderId": order_id, "items": event_data["items"]})

def process_inventory_reserved(db: SessionType, event_data: dict):
    order_id = event_data["orderId"]
    crud.update_order_status(db, order_id, OrderStatusEnum.CONFIRMED)
    # Final step: notify other services that order is confirmed
    publish_event("order_confirmed", {"orderId": order_id})

# --- Compensation Handlers (Fault Tolerance) ---
def process_payment_failed(db: SessionType, event_data: dict):
    order_id = event_data["orderId"]
    crud.update_order_status(db, order_id, OrderStatusEnum.FAILED)

def process_inventory_reservation_failed(db: SessionType, event_data: dict):
    order_id = event_data["orderId"]
    crud.update_order_status(db, order_id, OrderStatusEnum.FAILED)
    # Compensation: request a payment refund
    publish_event("refund_payment_request", {"orderId": order_id})

# Mapping topics to the functions that handle them
TOPIC_HANDLERS = {
    "payment_successful": process_payment_successful,
    "inventory_reserved": process_inventory_reserved,
    "payment_failed": process_payment_failed,
    "inventory_reservation_failed": process_inventory_reservation_failed,
}

def consume_events():
    """The main consumer loop. Subscribes to topics and processes messages."""
    conf = {
        'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
        'group.id': 'order_service_group',
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': False  # We will commit offsets manually for full control
    }
    consumer = Consumer(conf)
    consumer.subscribe(list(TOPIC_HANDLERS.keys()))
    logger.info(f"Kafka consumer subscribed to topics: {list(TOPIC_HANDLERS.keys())}")
    
    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                # This handles transport-level errors, not application errors
                logger.error(f"Kafka consumer error: {msg.error()}")
                continue
            
            topic = msg.topic()
            try:
                event_data = json.loads(msg.value().decode('utf-8'))
                logger.info(f"Consumed event from topic '{topic}'")
                
                handler = TOPIC_HANDLERS.get(topic)
                if handler:
                    db = SessionLocal()
                    try:
                        handler(db, event_data)
                        # On success, we commit the offset to Kafka so we don't process this message again
                        consumer.commit(asynchronous=False)
                        EVENTS_CONSUMED_TOTAL.labels(topic=topic).inc()
                    finally:
                        db.close()
                else:
                    logger.warning(f"No handler found for topic: {topic}. Discarding message.")
                    consumer.commit(asynchronous=False)
            
            except Exception as e:
                # This is our main application-level fault tolerance block.
                # If any part of the processing fails (DB down, bug in handler), we land here.
                # We will NOT commit the offset, so Kafka will redeliver the message after a timeout.
                # This acts as our retry mechanism. After a few retries, we'll send it to a DLQ.
                logger.error(f"FATAL: Unhandled exception processing event from topic '{topic}': {e}", exc_info=True)
                EVENTS_PROCESSING_FAILURES_TOTAL.labels(topic=topic).inc()
                
                # A proper DLQ would have a robust retry count, but for this project,
                # sending it immediately on first major failure is a sufficient demonstration of the pattern.
                dlq_topic = f"{topic}_dlq"
                logger.info(f"Sending poisonous message to DLQ topic: {dlq_topic}")
                try:
                    # Re-use our robust producer to send the failing message to the DLQ
                    publish_event(dlq_topic, {"original_message": msg.value().decode('utf-8'), "error": str(e)})
                    EVENTS_SENT_TO_DLQ_TOTAL.labels(topic=dlq_topic).inc()
                    # CRITICAL: We commit the offset of the original poison message so we don't process it again.
                    consumer.commit(asynchronous=False)
                except Exception as dlq_e:
                    logger.critical(f"CRITICAL FAILURE: Could not send message to DLQ. Error: {dlq_e}", exc_info=True)

    finally:
        consumer.close()
        logger.info("Kafka consumer has shut down.")

def start_consumer_thread():
    """Starts the Kafka consumer in a separate daemon thread."""
    consumer_thread = threading.Thread(target=consume_events, daemon=True)
    consumer_thread.start()