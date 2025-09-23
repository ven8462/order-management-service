from celery import shared_task
from orders.tasks import (
    handle_payment_successful,
    handle_payment_failed,
    handle_inventory_reserved,
    handle_inventory_failed,
    handle_inventory_timeout,
)

HANDLERS = {
    "payment-successful": handle_payment_successful,
    "payment-failed": handle_payment_failed,
    "inventory-reserved": handle_inventory_reserved,
    "inventory-failed": handle_inventory_failed,
    "inventory-timeout": handle_inventory_timeout,
}

@shared_task
def route_event(topic, event):
    handler = HANDLERS.get(topic)
    if handler:
        handler.delay(event)   # fan out to order.tasks
