
"""
This module manages Kafka event production with built-in fault tolerance.
It includes a circuit breaker to protect the application from a failing Kafka connection
and Prometheus metrics for monitoring.
"""

import json
import logging

from confluent_kafka import Producer
import pybreaker
from prometheus_client import Counter

from .config import settings

PRODUCER_EVENTS_TOTAL = Counter(
    "order_service_events_produced_total",
    "Total number of events successfully produced",
    ["topic"]
)
PRODUCER_FAILURES_TOTAL = Counter(
    "order_service_event_production_failures_total",
    "Total number of event production failures",
    ["topic"]
)

logger = logging.getLogger(__name__)

# --- Circuit Breaker Setup ---
# If the producer fails to flush a message 3 times in a row, the breaker will "open"
# for 60 seconds. During this time, any calls to publish_event will fail immediately
# without trying to contact Kafka. This protects our API from getting stuck.
breaker = pybreaker.CircuitBreaker(fail_max=3, reset_timeout=60)

# --- Singleton Kafka Producer ---
# We use a single producer instance for the entire application for efficiency.
kafka_producer = None

def get_kafka_producer():
    """Initializes and returns a singleton Kafka Producer instance."""
    global kafka_producer
    if kafka_producer is None:
        conf = {
            'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
            'acks': 'all',  # Ensure message is written to all replicas for durability
            'retries': 3,
            'retry.backoff.ms': 1000
        }
        kafka_producer = Producer(conf)
    return kafka_producer

@breaker
def publish_event(topic: str, event_data: dict):
    """
    Publishes an event to a Kafka topic. This function is decorated with the circuit breaker.
    
    Args:
        topic: The Kafka topic to publish to.
        event_data: A dictionary representing the event payload.
        
    Raises:
        pybreaker.CircuitBreakerError: If the circuit breaker is open.
        Exception: Re-raises Kafka-related exceptions on failure.
    """
    producer = get_kafka_producer()
    try:
        producer.produce(topic, value=json.dumps(event_data))
        result = producer.flush(timeout=5.0)
        
        if result > 0:
            raise RuntimeError(f"Failed to flush {result} messages from producer queue")

        # Increment success metric
        PRODUCER_EVENTS_TOTAL.labels(topic=topic).inc()
        logger.info(f"Successfully published event to topic '{topic}': {event_data}")

    except Exception as e:
        # Increment failure metric
        PRODUCER_FAILURES_TOTAL.labels(topic=topic).inc()
        logger.error(f"Failed to publish event to topic '{topic}': {e}", exc_info=True)
        raise