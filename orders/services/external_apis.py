import logging
from decimal import Decimal

import requests
from django.conf import settings
from pybreaker import CircuitBreakerError

from orders.utils.circuit_breaker import breaker_factory

logger = logging.getLogger(__name__)

# HTTP status codes
HTTP_CONFLICT = 409
HTTP_PAYMENT_REQUIRED = 402


class ServiceUnavailableError(Exception):
    pass


class InventoryReservationError(Exception):
    pass


class PaymentAuthorizationError(Exception):
    pass


def reserve_inventory(product_id: str, quantity: int, order_id: str) -> dict:
    """Call Inventory Service and raise exceptions on failure."""
    service_name = "INVENTORY"
    breaker = breaker_factory.get_breaker(service_name)
    url = f"http://inventory-service/inventory/{product_id}/reserve"

    try:

        @breaker
        def _do_request() -> dict:
            response = requests.post(
                url,
                json={"quantity": quantity, "orderId": order_id},
                timeout=settings.CB_INVENTORY_CALL_TIMEOUT,
            )
            if response.status_code == HTTP_CONFLICT:  # Out of stock
                raise InventoryReservationError(
                    response.json().get("detail", "Not enough stock"),
                )
            response.raise_for_status()
            return response.json()

        return _do_request()
    except CircuitBreakerError as err:
        msg = "Inventory Service is currently unavailable."
        raise ServiceUnavailableError(msg) from err
    except requests.RequestException as err:
        msg = f"Inventory Service request failed: {err}"
        raise ServiceUnavailableError(msg) from err


def release_inventory(reservation_id: str) -> None:
    """(Saga Compensation) Call Inventory Service to release stock."""
    try:
        requests.post(
            f"http://inventory-service/inventory/{reservation_id}/release",
            timeout=settings.CB_INVENTORY_CALL_TIMEOUT,
        ).raise_for_status()
    except requests.RequestException as err:
        logger.critical(
            "FATAL: Compensation failed for reservation %s. Manual cleanup required. Error: %s",
            reservation_id,
            err,
        )


def authorize_payment(
    user_id: str,
    payment_method_id: str,
    total: Decimal,
    currency: str,
    idempotency_key: str,
) -> dict:
    """Call Payment Service and raise exceptions on failure."""
    service_name = "PAYMENT"
    breaker = breaker_factory.get_breaker(service_name)
    url = "http://payment-service/payments/authorize"

    try:

        @breaker
        def _do_request() -> dict:
            response = requests.post(
                url,
                json={
                    "user_id": user_id,
                    "payment_method_id": payment_method_id,
                    "amount": str(total),
                    "currency": currency,
                    "idempotency_key": idempotency_key,
                },
                timeout=settings.CB_PAYMENT_CALL_TIMEOUT,
            )
            if response.status_code == HTTP_PAYMENT_REQUIRED:
                raise PaymentAuthorizationError(
                    response.json().get("detail", "Payment was declined"),
                )
            response.raise_for_status()
            return response.json()

        return _do_request()
    except CircuitBreakerError as err:
        msg = "Payment Service is currently unavailable."
        raise ServiceUnavailableError(msg) from err
    except requests.RequestException as err:
        msg = f"Payment Service request failed: {err}"
        raise ServiceUnavailableError(msg) from err
