import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import crud, inventory_client, producer, schema
from .database import get_db
from .inventory_client import InventoryServiceError
from .models import OrderStatusEnum

logger = logging.getLogger(__name__)

order_router = APIRouter(prefix="/orders", tags=["Order Management"])


@order_router.post("/", response_model=schema.Order, status_code=status.HTTP_201_CREATED)
def create_order(
    order_create: schema.OrderCreate,
    db: Annotated[Session, Depends(get_db)],
) -> schema.Order:
    try:
        db_order = crud.create_order(db=db, order=order_create)
        event_payload = {
            "orderId": db_order.id,
            "userId": db_order.user_id,
            "totalAmount": db_order.total_amount,
            "items": [item.dict() for item in order_create.items],
        }
        producer.publish_event("process_payment_request", event_payload)
        return crud.update_order_status(
            db,
            db_order.id,
            OrderStatusEnum.PAYMENT_PROCESSING,
        )
    except Exception as e:
        logger.exception("Failed to create order or publish event: %s", e)
        crud.update_order_status(db, db_order.id, OrderStatusEnum.FAILED)
        raise HTTPException(
            status_code=503,
            detail="Service is currently unavailable to process new orders.",
        ) from e


@order_router.get("/", response_model=list[schema.Order])
def retrieve_orders_by_user(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> list[schema.Order]:
    return crud.get_orders_by_user(db, user_id=user_id)


@order_router.get("/{order_id}", response_model=schema.Order)
def retrieve_order(order_id: int, db: Annotated[Session, Depends(get_db)]) -> schema.Order:
    db_order = crud.get_order(db, order_id=order_id)
    if db_order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return db_order


@order_router.put(
    "/{order_id}/status",
    response_model=schema.Order,
    tags=["Order Management", "Admin"],
)
def update_order_status_manually(
    order_id: int,
    status_update: schema.OrderStatusUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> schema.Order:
    db_order = crud.get_order(db, order_id)
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    return crud.update_order_status(db, order_id=order_id, status=status_update.status)


@order_router.get("/{order_id}/tracking", response_model=list[schema.OrderStatusHistory])
def get_order_tracking_history(
    order_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> list[schema.OrderStatusHistory]:
    history = crud.get_order_status_history(db, order_id=order_id)
    if not history:
        db_order = crud.get_order(db, order_id=order_id)
        if db_order is None:
            raise HTTPException(status_code=404, detail="Order not found")
    return history


cart_router = APIRouter(prefix="/cart", tags=["Shopping Cart"])


@cart_router.post("/items", response_model=schema.Cart)
def add_to_cart(
    item_create: schema.CartItemCreate,
    db: Annotated[Session, Depends(get_db)],
) -> schema.Cart:
    return crud.add_item_to_cart(db=db, user_id=item_create.user_id, item=item_create)


@cart_router.get("/{user_id}", response_model=schema.Cart)
def get_user_cart(user_id: int, db: Annotated[Session, Depends(get_db)]) -> schema.Cart:
    cart = crud.get_cart_with_total(db=db, user_id=user_id)
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found for this user.")
    return cart


product_router = APIRouter(prefix="/products", tags=["Product Catalog (Proxy)"])


@product_router.get("/search")
def product_search_proxy(q: str = "", category: str = "", limit: int = 10, page: int = 1) -> dict:
    try:
        return inventory_client.search_products(
            query=q,
            category=category,
            limit=limit,
            page=page,
        )
    except InventoryServiceError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


monitoring_router = APIRouter(tags=["Monitoring"])


@monitoring_router.get("/health/ping", status_code=status.HTTP_200_OK)
def health_check(db: Annotated[Session, Depends(get_db)]) -> dict:
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        logger.exception("Health check failed: Database connection error")
        raise HTTPException(
            status_code=503,
            detail={"status": "error", "database": "disconnected"},
        ) from e
    else:
        return {"status": "ok", "database": "connected"}
