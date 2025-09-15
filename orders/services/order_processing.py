import logging
import uuid
from decimal import Decimal

from django.db import transaction

from orders.models import Order, OrderItem, OrderTracking

from . import external_apis
from .external_apis import (
    InventoryReservationError,
    PaymentAuthorizationError,
    ServiceUnavailableError,
)

logger = logging.getLogger(__name__)


def create_order_saga(  # noqa: PLR0913
    user_id: str,
    items: list,
    address_id: str,
    payment_method_id: str,
    currency: str,
    idempotency_key: str,
) -> Order:
    order_id = str(uuid.uuid4())
    reservations_made: list[str] = []

    # Step 1: Reserve inventory
    for item in items:
        try:
            reservation = external_apis.reserve_inventory(
                product_id=str(item["product_id"]),
                quantity=item["quantity"],
                order_id=order_id,
            )
            reservations_made.append(reservation.get("reservationId"))
        except (InventoryReservationError, ServiceUnavailableError):
            logger.exception(
                "[Order: %s] Saga failed at inventory reservation. Compensating...",
                order_id,
            )
            for res_id in reservations_made:
                external_apis.release_inventory(res_id)
            raise

    # Step 2: Authorize payment
    total = sum(Decimal(str(it["price"])) * int(it["quantity"]) for it in items)
    try:
        payment_data = external_apis.authorize_payment(
            user_id,
            payment_method_id,
            total,
            currency,
            idempotency_key,
        )
    except (PaymentAuthorizationError, ServiceUnavailableError):
        logger.exception(
            "[Order: %s] Saga failed at payment authorization. Compensating...",
            order_id,
        )
        for res_id in reservations_made:
            external_apis.release_inventory(res_id)
        raise

    # Step 3: Persist order
    with transaction.atomic():
        order = Order.objects.create(
            id=order_id,
            user_id=user_id,
            status=Order.Status.PENDING,
            total_amount=total,
            currency=currency,
            address_id=address_id,
            payment_method_id=payment_method_id,
            payment_transaction_id=payment_data.get("transaction_id"),
        )
        OrderItem.objects.bulk_create(
            [
                OrderItem(
                    order=order,
                    product_id=it["product_id"],
                    quantity=it["quantity"],
                    price=it["price"],
                    subtotal=Decimal(str(it["price"])) * int(it["quantity"]),
                )
                for it in items
            ],
        )
        OrderTracking.objects.create(
            order=order,
            status=Order.Status.PENDING,
            location="Order Placed",
        )

    logger.info("[Order: %s] Saga completed successfully.", order_id)
    return order
