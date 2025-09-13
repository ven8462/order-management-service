"""Placeholders for external service interactions."""

from decimal import Decimal
from typing import Any


# Catalog client
def product_search(
    query: str,
    category: str | None = None,
    limit: int = 10,
    page: int = 1,
) -> dict[str, Any]:
    # In prod, call Catalog API. Here return a stubbed response.
    products = [
        {
            "productId": "00000000-0000-0000-0000-000000000001",
            "name": "Running Shoes",
            "price": Decimal("60.00"),
            "currency": "USD",
            "availability": "IN_STOCK",
        },
    ]
    return {
        "products": products,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": len(products),
        },
    }


def get_product(product_id: str) -> dict[str, Any]:
    # Replace with actual GET to catalog
    return {
        "productId": product_id,
        "name": "Sample Product",
        "price": Decimal("10.00"),
        "currency": "USD",
        "availability": "IN_STOCK",
    }


# Inventory client
def reserve_inventory(product_id: str, quantity: int) -> bool:
    # Call Inventory service to reserve stock. Return True if reserved.
    return True


# Payment client
def authorize_payment(
    user_id: str,
    payment_method_id: str,
    amount: Decimal,
    currency: str,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    # Replace with real payment provider integration.
    return {
        "success": True,
        "transaction_id": "txn-{}".format(idempotency_key or "auto"),
    }


# User service (address)
def get_user_address(user_id: str, address_id: str) -> dict[str, Any]:
    # Replace with call to user service
    return {
        "addressId": address_id,
        "line": "Bennix apartments, westlands",
    }
