import pytest
from unittest.mock import patch
from orders.tasks import (
    handle_payment_successful,
    handle_payment_failed,
    handle_inventory_reserved,
    handle_inventory_failed,
    handle_inventory_timeout,
)
from orders.models import Order, OrderTracking

@pytest.mark.django_db
@patch("orders.tasks.publish_event")
def test_handle_payment_successful(mock_publish, pending_order):
    event = {"order_id": pending_order.id, "items": ["item1"]}

    handle_payment_successful(event)

    pending_order.refresh_from_db()
    assert pending_order.status == Order.Status.PAID
    tracking = OrderTracking.objects.get(order=pending_order)
    assert tracking.location == "Payment Successful"
    mock_publish.assert_called_once_with(
        "reserve-inventory", {"order_id": pending_order.id, "items": event["items"]}
    )

@pytest.mark.django_db
def test_handle_payment_failed(pending_order):
    event = {"order_id": pending_order.id}

    handle_payment_failed(event)

    pending_order.refresh_from_db()
    assert pending_order.status == Order.Status.CANCELLED
    tracking = OrderTracking.objects.get(order=pending_order)
    assert tracking.location == "Payment Failed"

@pytest.mark.django_db
def test_handle_inventory_reserved(pending_order):
    event = {"order_id": pending_order.id}

    handle_inventory_reserved(event)

    pending_order.refresh_from_db()
    assert pending_order.status == Order.Status.COMPLETED
    tracking = OrderTracking.objects.get(order=pending_order)
    assert tracking.location == "Inventory Reserved"

@pytest.mark.django_db
@patch("orders.tasks.publish_event")
def test_handle_inventory_failed(mock_publish, pending_order):
    event = {"order_id": pending_order.id}

    handle_inventory_failed(event)

    pending_order.refresh_from_db()
    assert pending_order.status == Order.Status.CANCELLED
    tracking = OrderTracking.objects.get(order=pending_order)
    assert tracking.location == "Inventory Failed"
    mock_publish.assert_called_once_with("cancel-payment", {"order_id": pending_order.id})

@pytest.mark.django_db
@patch("orders.tasks.publish_event")
def test_handle_inventory_timeout(mock_publish, pending_order):
    event = {"order_id": pending_order.id}

    handle_inventory_timeout(event)

    pending_order.refresh_from_db()
    assert pending_order.status == Order.Status.CANCELLED
    tracking = OrderTracking.objects.get(order=pending_order)
    assert tracking.location == "Inventory Timeout"
    mock_publish.assert_called_once_with("cancel-payment", {"order_id": pending_order.id})