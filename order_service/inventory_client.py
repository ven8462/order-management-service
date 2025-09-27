import logging
import os

import httpx
import pybreaker

logger = logging.getLogger(__name__)

INVENTORY_SERVICE_BASE_URL = os.getenv("INVENTORY_SERVICE_URL", "http://inventory-service:8000")

headers = {"ngrok-skip-browser-warning": "true"}

inventory_breaker = pybreaker.CircuitBreaker(fail_max=5, reset_timeout=60)

client = httpx.Client(base_url=INVENTORY_SERVICE_BASE_URL, timeout=10.0, headers=headers)


class InventoryServiceError(Exception):
    pass


@inventory_breaker
def reserve_stock(order_id: int, user_id: int, items: list[dict]) -> bool | None:
    logger.info(
        "Contacting Inventory service at %s for order %s",
        INVENTORY_SERVICE_BASE_URL,
        order_id,
    )
    try:
        for item in items:
            payload = {"quantity": item["quantity"], "user_id": user_id, "order_id": order_id}
            response = client.post(
                f"/api/reservations/{item['product_id']}/reserve/",
                json=payload,
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        error_detail = e.response.json().get("detail", e.response.text)
        logger.exception(
            "Inventory service rejected reservation for order %s: %s",
            order_id,
            error_detail,
        )
        msg = f"Inventory rejected reservation: {error_detail}"
        raise InventoryServiceError(msg) from e
    except (httpx.RequestError, pybreaker.CircuitBreakerError) as e:
        logger.exception("Inventory service is unavailable for order %s: %s", order_id, e)
        msg = f"Inventory service is unavailable: {e}"
        raise InventoryServiceError(msg) from e
    else:
        logger.info("Successfully reserved stock for order %s", order_id)
        return True
