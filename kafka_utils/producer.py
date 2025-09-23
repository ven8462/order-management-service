import json
import time
from kafka import KafkaProducer, errors

_producer = None

def get_producer():
    global _producer
    if _producer is None:
        _producer = KafkaProducer(
            bootstrap_servers="kafka:9092",
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            retries=5,  # Kafka internal retries
        )
    return _producer


def publish_event(topic, event, max_retries=3, backoff=2):
    """
    Publish an event to Kafka with retry logic.

    :param topic: Kafka topic name
    :param event: dict payload
    :param max_retries: max retry attempts
    :param backoff: base sleep seconds between retries (exponential backoff)
    """
    producer = get_producer()
    attempt = 0

    while attempt <= max_retries:
        try:
            future = producer.send(topic, event)
            future.get(timeout=10)  # block until acknowledged
            return True
        except (errors.KafkaError, Exception) as e:
            attempt += 1
            if attempt > max_retries:
                print(f"[KafkaProducer] Failed to send event to {topic}: {e}")
                return False
            sleep_time = backoff * attempt
            print(f"[KafkaProducer] Retry {attempt}/{max_retries} in {sleep_time}s...")
            time.sleep(sleep_time)