import logging
import os

import httpx
import pybreaker

logger = logging.getLogger(__name__)

PAYMENT_SERVICE_BASE_URL = os.getenv("PAYMENT_SERVICE_URL", "https://nonoffensive-suasively-lorri.ngrok-free.dev")
HEADERS = {"ngrok-skip-browser-warning": "true"}

payment_breaker = pybreaker.CircuitBreaker(fail_max=5, reset_timeout=60)
client = httpx.Client(base_url=PAYMENT_SERVICE_BASE_URL, timeout=10.0, headers=HEADERS)


class PaymentServiceError(Exception):
    pass


@payment_breaker
def create_payment(
    order_id: str,
    amount: float,
    items: list[dict],
    shipping_address: str,
    user_id: str | None = None,
    user_info: dict | None = None,
    gateway: str = "paystack",
    test_mode: bool = True,
    retry: bool = False,
) -> dict:
    payload = {
        "userId": user_id,
        "orderId": order_id,
        "amount": amount,
        "retry": retry,
        "metadata": {
            "order": {
                "id": order_id,
                "description": f"Order payment for {len(items)} item(s)",
                "items": [item["name"] for item in items],
                "totalItems": len(items),
                "shippingAddress": shipping_address,
            },
            "user": user_info,
            "gateway": gateway,
            "testMode": test_mode,
        },
    }

    try:
        response = client.post("/payments", json=payload)
        response.raise_for_status()
        data = response.json().get("data", {})

        status = data.get("status")
        if not status:
            logger.warning(
                "Payment response missing status for order %s. Marking as PROCESSING.",
                 order_id
                 )
            status = "PAYMENT_PROCESSING"

        return {"status": status, "data": data}

    except httpx.HTTPStatusError as e:
        try:
            error = e.response.json().get("error", {})
        except Exception:
            error = {"message": e.response.text, "status": e.response.status_code}

        # Map HTTP errors to payment outcome
        if e.response.status_code == 409:  # Conflict: Payment already exists
            existing_payment_id = e.response.json().get("details", {}).get("existingPaymentId")
            return {"status": "SUCCEEDED", "data": {"id": existing_payment_id}}
        elif e.response.status_code in (400, 401):
            return {"status": "FAILED", "error": error}
        elif e.response.status_code in (429, 500, 502):
            return {"status": "PAYMENT_PROCESSING", "error": error}
        else:
            return {"status": "PAYMENT_PROCESSING", "error": error}

    except (httpx.RequestError, pybreaker.CircuitBreakerError) as e:
        logger.exception("Payment service unavailable for order %s: %s", order_id, e)
        return {"status": "PAYMENT_PROCESSING", "error": {"message": str(e)}}
