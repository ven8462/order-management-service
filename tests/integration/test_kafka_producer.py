from unittest.mock import patch
from kafka_utils.producer import producer

def test_producer_send():
    with patch.object(producer, "send") as mock_send:
        event = {"order_id": 123}
        producer.send("payments", event)
        mock_send.assert_called_once_with("payments", event)