import pytest
from unittest.mock import patch
from kafka_utils.consumer import process_event

@pytest.mark.django_db
@patch("orders.tasks.handle_payment_successful.delay")
def test_consumer_dispatch(mock_delay):
    event = {"type": "PaymentSuccessful", "order_id": 1}

    process_event(event)

    mock_delay.assert_called_once_with(1)