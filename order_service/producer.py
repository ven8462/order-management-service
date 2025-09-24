import json
import logging

import pybreaker
from confluent_kafka import Producer
from prometheus_client import Counter

from .config import settings

PRODUCER_EVENTS_TOTAL = Counter(
    "order_service_events_produced_total",
    "Total number of events successfully produced",
    ["topic"],
)
PRODUCER_FAILURES_TOTAL = Counter(
    "order_service_event_production_failures_total",
    "Total number of event production failures",
    ["topic"],
)

logger = logging.getLogger(__name__)

breaker = pybreaker.CircuitBreaker(fail_max=3, reset_timeout=60)


class KafkaProducerSingleton:
    _instance = None

    def __new__(cls) -> "KafkaProducerSingleton":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            conf = {
                "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
                "acks": "all",
                "retries": 3,
                "retry.backoff.ms": 1000,
            }
            cls._instance.producer = Producer(conf)
        return cls._instance


def get_kafka_producer() -> Producer:
    return KafkaProducerSingleton().producer


def _raise_flush_error(result: int, topic: str) -> None:
    msg = f"Failed to flush {result} messages from producer queue"
    raise RuntimeError(msg)


@breaker
def publish_event(topic: str, event_data: dict) -> None:
    producer = get_kafka_producer()
    try:
        producer.produce(topic, value=json.dumps(event_data))
        result = producer.flush(timeout=5.0)

        if result > 0:
            _raise_flush_error(result, topic)

        PRODUCER_EVENTS_TOTAL.labels(topic=topic).inc()
        logger.info("Successfully published event to topic '%s': %s", topic, event_data)

    except Exception as e:
        PRODUCER_FAILURES_TOTAL.labels(topic=topic).inc()
        logger.exception("Failed to publish event to topic '%s': %s", topic, e)
        raise
