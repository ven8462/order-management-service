from celery import shared_task
from .models import Order, OrderTracking
from kafka_utils.producer import publish_event


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def handle_payment_successful(self, event):
    try:
        order = Order.objects.filter(id=event["order_id"]).first()
        if not order:
            return

        order.status = Order.Status.PAID
        order.save(update_fields=["status", "updated_at"])

        OrderTracking.objects.create(
            order=order,
            status=order.status,
            location="Payment Successful"
        )

        publish_event("reserve-inventory", {
            "order_id": order.id,
            "items": event.get("items", [])
        })

        print(f"Payment successful for order {order.id}")
    except Exception as e:
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def handle_payment_failed(self, event):
    try:
        order = Order.objects.filter(id=event["order_id"]).first()
        if not order:
            return

        order.status = Order.Status.CANCELLED
        order.save(update_fields=["status", "updated_at"])

        OrderTracking.objects.create(
            order=order,
            status=order.status,
            location="Payment Failed"
        )

        print(f"Payment failed for order {order.id}")
    except Exception as e:
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def handle_inventory_reserved(self, event):
    try:
        order = Order.objects.filter(id=event["order_id"]).first()
        if not order:
            return

        order.status = Order.Status.COMPLETED
        order.save(update_fields=["status", "updated_at"])

        OrderTracking.objects.create(
            order=order,
            status=order.status,
            location="Inventory Reserved"
        )

        print(f"Inventory reserved for order {order.id}")
    except Exception as e:
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def handle_inventory_failed(self, event):
    try:
        order = Order.objects.filter(id=event["order_id"]).first()
        if not order:
            return

        order.status = Order.Status.CANCELLED
        order.save(update_fields=["status", "updated_at"])

        OrderTracking.objects.create(
            order=order,
            status=order.status,
            location="Inventory Failed"
        )

        publish_event("cancel-payment", {"order_id": order.id})

        print(f"Inventory reservation failed, cancelled order {order.id}")
    except Exception as e:
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def handle_inventory_timeout(self, event):
    try:
        order = Order.objects.filter(id=event["order_id"]).first()
        if not order:
            return

        order.status = Order.Status.CANCELLED
        order.save(update_fields=["status", "updated_at"])

        OrderTracking.objects.create(
            order=order,
            status=order.status,
            location="Inventory Timeout"
        )

        publish_event("cancel-payment", {"order_id": order.id})

        print(f"Inventory reservation timed out, cancelled order {order.id}")
    except Exception as e:
        raise self.retry(exc=e)