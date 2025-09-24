# File: order_service/api.py
"""
This module defines the API endpoints for the Order Management Service.
It follows RESTful principles and an event-driven, non-blocking architecture.
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from . import crud, schemas
from kafka_utils import producer
from .database import get_db
from .models import OrderStatusEnum

# Initialize a logger for this module
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orders", tags=["Orders"])

@router.post("/", response_model=schemas.Order, status_code=status.HTTP_201_CREATED)
def create_order(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    """
    Creates a new order and initiates the Saga by publishing a 'process_payment_request' event.

    This is the primary "write" endpoint. It is designed to be fast and non-blocking.
    It returns immediately after accepting the order and starting the background process.
    """
    try:
        # 1. Create the order in the database with a PENDING status.
        db_order = crud.create_order(db=db, order=order)

        # 2. Prepare the event payload for the Kafka message.
        event_payload = {
            "orderId": db_order.id,
            "userId": db_order.user_id,
            "totalAmount": db_order.total_amount,
            "items": [item.dict() for item in order.items]
        }
        
        # 3. Publish the event to start the Saga. This replaces a slow, synchronous API call.
        producer.publish_event("process_payment_request", event_payload)

        # 4. Immediately update the status to show the saga has started and return the *updated* object.
        updated_order = crud.update_order_status(db, db_order.id, OrderStatusEnum.PAYMENT_PROCESSING)
        return updated_order

    except Exception as e:
        logger.error(f"Failed to create order or publish event: {e}", exc_info=True)
        # If event publishing fails, mark the order as FAILED to prevent "zombie" orders.
        crud.update_order_status(db, db_order.id, OrderStatusEnum.FAILED)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service is currently unavailable to process new orders."
        )

@router.get("/{order_id}", response_model=schemas.Order)
def retrieve_order(order_id: int, db: Session = Depends(get_db)):
    """
    Retrieves the current details and status of a specific order by its ID.
    """
    db_order = crud.get_order(db, order_id=order_id)
    if db_order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return db_order

@router.get("/", response_model=List[schemas.Order])
def retrieve_orders_by_user(user_id: int, db: Session = Depends(get_db)):
    """
    Retrieves a list of all orders for a specific user.
    This uses a query parameter for filtering, which is a standard REST practice.
    Example: GET /orders?user_id=123
    """
    # NOTE: You could expand this for admin use, e.g., if user_id is None, return all orders.
    return crud.get_orders_by_user(db, user_id=user_id)

@router.put(
    "/{order_id}/status", 
    response_model=schemas.Order, 
    tags=["Admin"],
    summary="Manually update order status"
)
def update_order_status_manually(
    order_id: int,
    status_update: schemas.OrderStatusUpdate,
    db: Session = Depends(get_db)
):
    """
    Manually overrides the status of an order. This endpoint should be protected
    and used for administrative purposes or internal testing only, as the primary
    status flow is managed by the event-driven Saga.
    """
    db_order = crud.get_order(db, order_id)
    if not db_order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return crud.update_order_status(db, order_id=order_id, status=status_update.status)

@router.get("/health/ping", status_code=status.HTTP_200_OK, tags=["Monitoring"])
def health_check(db: Session = Depends(get_db)):
    """
    Provides a health check endpoint for monitoring and uptime verification.
    It verifies connectivity to essential services like the database.
    """
    try:
        db.execute("SELECT 1")
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: Database connection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail={"status": "error", "database": "disconnected"}
        )

@router.get("/{order_id}/order_history", response_model=List[schemas.OrderStatusHistory])
def order_history(order_id: int, db: Session = Depends(get_db)):
    """
    Track order status/progress by order_id
    """
    order_history = crud.get_order_history(db, order_id=order_id)

    if order_history is None or len(order_history) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No status history found for order {order_id}"
        )

    return order_history